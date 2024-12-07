import pandas as pd
from sklearn.cluster import KMeans
from table import Warehouse,AgentsBigPic,OrdersBigPic
import numpy as np
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import and_,delete,update
import gc
from fastdist import fastdist
from utils import solve_tsp,dist_between_points
import random

max_orders_per_agent = 60
max_distance_per_agent = 100

def round_robin_allocation(session, undelivered_orders, agents, max_orders_per_agent, max_distance_per_agent, warehouse_id):
    """
    Allocate orders to agents using a round-robin approach.
    """
    warehouse_coords = session.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    warehouse_x, warehouse_y = warehouse_coords.x_coord, warehouse_coords.y_coord

    agent_cycle = iter(agents)
    for order_data in undelivered_orders:
        order_id, order_x, order_y = order_data
        assigned = False

        # Keep iterating through agents until we find one that can accept the order
        while not assigned:
            try:
                agent = next(agent_cycle)
            except StopIteration:
                # Restart the cycle if we've exhausted all agents
                agent_cycle = iter(agents)
                agent = next(agent_cycle)

            session.refresh(agent)

            if agent.no_of_orders >= max_orders_per_agent:
                continue

            if agent.no_of_orders > 0:
                # Calculate distance from the last order
                prev_order_id = agent.orders[-1]
                prev_order = session.query(OrdersBigPic).filter(OrdersBigPic.id == prev_order_id).first()
                distance_to_add = dist_between_points(order_x, order_y, prev_order.x_coord, prev_order.y_coord)
            else:
                # Calculate distance from the warehouse
                distance_to_add = dist_between_points(order_x, order_y, warehouse_x, warehouse_y)

            if agent.total_distance + distance_to_add > max_distance_per_agent:
                continue

            # Assign the order to this agent
            order = session.query(OrdersBigPic).filter(OrdersBigPic.id == order_id).first()
            order.is_delivered = True
            order.assigned_agent = agent.id
            agent.no_of_orders += 1
            agent.total_distance += distance_to_add

            if agent.orders is None:
                agent.orders = []
            agent.orders.append(order_id)

            flag_modified(agent, 'orders')
            session.flush()
            session.commit()
            assigned = True

def allocate_warehouse_orders(session,warehouse_id,max_orders_per_agent=60,max_distance_per_agent=100):
    
    
    orders = session.query(OrdersBigPic.id, OrdersBigPic.x_coord, OrdersBigPic.y_coord).filter(and_(OrdersBigPic.warehouse_id == warehouse_id,OrdersBigPic.is_delivered == False)).limit(1200).all()
    orders_df = pd.DataFrame(orders, columns=["id", "x_coord", "y_coord"])
    
    agents = session.query(AgentsBigPic).filter(
            and_(
                AgentsBigPic.warehouse_id == warehouse_id,
                AgentsBigPic.is_checked_in == True
            )
        ).all()
    
    if agents is None:
        return
    
    if len(orders) < len(agents):
            print("Switching to round-robin allocation due to insufficient data points.")
            round_robin_allocation(session, orders, agents, max_orders_per_agent, max_distance_per_agent, warehouse_id)
            return
    
    kmeans = KMeans(n_clusters=len(agents), random_state=42)
    orders_df['cluster'] = kmeans.fit_predict(orders_df[['x_coord', 'y_coord']])


    for cluster_id,agent in enumerate(agents):
        session.refresh(agent)

        cluster_orders = orders_df[orders_df['cluster']==cluster_id]
        if agent.orders is None:
            agent.orders = []
        
        current_orders = list(agent.orders) if agent.orders else []
        
        coordinates = cluster_orders[['x_coord', 'y_coord']].to_numpy()

        if len(coordinates) > 1:
            distance_matrix = fastdist.matrix_pairwise_distance(coordinates, fastdist.euclidean, 'euclidean',return_matrix=True)

            tsp_route = solve_tsp(distance_matrix)

            # Free memory after calculating TSP
            del distance_matrix
            gc.collect()
        else:
            tsp_route = [0]
        #for idx,row in cluster_orders.iterrows():
        for idx in tsp_route:
            # print("idx:",idx)
            order_id = cluster_orders.iloc[idx]['id']
            # print("order_id",order_id)
            if agent.no_of_orders >= max_orders_per_agent:
                    break

            order = session.query(OrdersBigPic).filter(OrdersBigPic.id == order_id).first()

            if agent.no_of_orders > 0:
                    # print("agent_id", agent.id)
                    # print("no_of_orders inside the prev point calc:", agent.no_of_orders)
                    # print("inside if, orders_list:", current_orders)
                    prev_order_index = len(current_orders) - 1
                    prev_order = session.query(OrdersBigPic).filter(OrdersBigPic.id == current_orders[prev_order_index]).first()
                    distance_to_add = dist_between_points(order.x_coord, order.y_coord, prev_order.x_coord, prev_order.y_coord)
            else:
                warehouse_coords = session.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
                warehouse_x = warehouse_coords.x_coord
                warehouse_y = warehouse_coords.y_coord
                distance_to_add = dist_between_points(order.x_coord, order.y_coord, warehouse_x, warehouse_y)

            if agent.total_distance + distance_to_add > max_distance_per_agent:
                continue

            current_orders.append(order.id)
            order.agent_id = agent.id
            # print("agent_id:", agent.id)
            # print("order_to_be_appended:", order.id)
            # print("no_of_orders:", agent.no_of_orders)
            # print("order_list_after_append:", current_orders)
            
            agent.no_of_orders += 1
            agent.total_distance += distance_to_add
            order.is_delivered = True
            order.assigned_agent = agent.id

        # Explicitly update the orders column
        agent.orders = current_orders
        
        # Force SQLAlchemy to recognize the change
        flag_modified(agent, 'orders')
        
        # Commit changes and refresh
        session.flush()
        session.commit()
        session.refresh(agent)
        
        # print(f"After commit, agent {agent.id} has orders: {agent.orders}")

def recluster_and_reassign(session, agents,warehouse_id, max_orders_per_agent=max_orders_per_agent, max_distance_per_agent=max_distance_per_agent):
    while True:
        if agents is None:
            break
        undelivered_orders = session.query(OrdersBigPic.id, OrdersBigPic.x_coord, OrdersBigPic.y_coord).filter(and_(OrdersBigPic.warehouse_id == warehouse_id,OrdersBigPic.is_delivered == False)).limit(720).all()

        if not undelivered_orders:
            print("All orders have been delivered.")
            break

        undelivered_df = pd.DataFrame(undelivered_orders, columns=["id", "x_coord", "y_coord"])

        available_agents = [
            agent for agent in agents
            if agent.is_checked_in and agent.no_of_orders < max_orders_per_agent and agent.total_distance < max_distance_per_agent
        ]

        if not available_agents:
            print("No available agents to assign remaining orders.")
            break

        if len(undelivered_df) < len(available_agents):
            print("Switching to round-robin allocation due to insufficient data points.")
            round_robin_allocation(session, undelivered_orders, available_agents, max_orders_per_agent, max_distance_per_agent, warehouse_id)
            break

        agent_start_points = [
            (session.query(OrdersBigPic).filter(OrdersBigPic.id == agent.orders[-1]).first().x_coord,
             session.query(OrdersBigPic).filter(OrdersBigPic.id == agent.orders[-1]).first().y_coord)
            if agent.orders else (0, 0)
            for agent in available_agents
        ]

        
        kmeans = KMeans(n_clusters=len(agent_start_points), init=np.array(agent_start_points), n_init=1, random_state=42)
        undelivered_df['cluster'] = kmeans.fit_predict(undelivered_df[['x_coord', 'y_coord']])

        
        orders_assigned = False
        for cluster_id, agent in enumerate(available_agents):
            # Make sure we're working with the latest agent data
            session.refresh(agent)
            
            cluster_orders = undelivered_df[undelivered_df['cluster'] == cluster_id]

            # Initialize orders list if None
            if agent.orders is None:
                agent.orders = []
            
            # Create a new list for orders to ensure change tracking
            current_orders = list(agent.orders) if agent.orders else []
        
            coordinates = cluster_orders[['x_coord', 'y_coord']].to_numpy()

            if len(coordinates) > 1:
                
                distance_matrix = fastdist.matrix_pairwise_distance(coordinates, fastdist.euclidean, 'euclidean',return_matrix=True)

                
                tsp_route = solve_tsp(distance_matrix)

                
                del distance_matrix
                gc.collect()
            else:
                
                tsp_route = [0]
            #for idx,row in cluster_orders.iterrows():
            for idx in tsp_route:
                # print("idx:",idx)
                order_id = cluster_orders.iloc[idx]['id']

                # Check agent constraints
                if agent.no_of_orders >= max_orders_per_agent:
                    break

                order = session.query(OrdersBigPic).filter(OrdersBigPic.id == order_id).first()

                if agent.no_of_orders > 0:
                    # print("agent_id", agent.id)
                    # print("no_of_orders inside the prev point calc:", agent.no_of_orders)
                    # print("inside if, orders_list:", current_orders)
                    prev_order_index = len(current_orders) - 1
                    prev_order = session.query(OrdersBigPic).filter(OrdersBigPic.id == current_orders[prev_order_index]).first()
                    distance_to_add = dist_between_points(order.x_coord, order.y_coord, prev_order.x_coord, prev_order.y_coord)
                else:
                    warehouse_coords = session.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
                    warehouse_x = warehouse_coords.x_coord
                    warehouse_y = warehouse_coords.y_coord
                    distance_to_add = dist_between_points(order.x_coord, order.y_coord, warehouse_x, warehouse_y)

                if agent.total_distance + distance_to_add > max_distance_per_agent:
                    continue

                # Append to our working copy of orders
                current_orders.append(order.id)
                # print("agent_id:", agent.id)
                # print("order_to_be_appended:", order.id)
                # print("no_of_orders:", agent.no_of_orders)
                # print("order_list_after_append:", current_orders)
                
                # Update agent fields
                agent.no_of_orders += 1
                agent.total_distance += distance_to_add
                order.is_delivered = True
                orders_assigned = True
                order.assigned_agent = agent.id

            # Explicitly update the orders column
            agent.orders = current_orders
            
            # Force SQLAlchemy to recognize the change
            flag_modified(agent, 'orders')
            
            # Commit changes and refresh
            session.flush()
            session.commit()
            session.refresh(agent)
            
            # print(f"After commit, agent {agent.id} has orders: {agent.orders}")
            
        agents = session.query(AgentsBigPic).filter(
            and_(
                AgentsBigPic.warehouse_id == warehouse_id,
                AgentsBigPic.is_checked_in == True
            )
        ).all()

        # Step 5: Break the loop if no orders were assigned in this iteration
        if not orders_assigned:
            print("No further assignments possible within constraints.")
            break

def mark_agent_check_in(session):
    agents = session.query(AgentsBigPic).all()

    if not agents:
        return None

    
    attnd_percentage = random.randint(60,90)
    no_of_present_agents = int((attnd_percentage/100) * len(agents))

    selected_agents = random.sample(agents, no_of_present_agents)

    for agent in selected_agents:
        agent.is_checked_in = True 
    
    session.commit()

    return len(selected_agents)

def mark_all_checked_out(session):
    session.query(AgentsBigPic).update({AgentsBigPic.is_checked_in: False})
    session.commit()

    #pop all orders that were delivered
    session.execute(
        delete(OrdersBigPic).where(OrdersBigPic.is_delivered == True)
    )
    session.commit()

    session.query(AgentsBigPic).update({AgentsBigPic.orders: [],AgentsBigPic.no_of_orders:0,AgentsBigPic.total_distance:0})

    session.commit()

    return 1

def calculate_earnings(session,agent_id):
    agent = session.query(AgentsBigPic).filter(AgentsBigPic.id == agent_id).first()
    total_earnings = 0
    if agent.is_checked_in:
        total_earnings = 500
        if agent.no_of_orders > 50:
            total_earnings = 42 * agent.no_of_orders
        elif agent.no_of_orders > 25:
            total_earnings = 35 * agent.no_of_orders

    return total_earnings
