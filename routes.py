import falcon
from allocation_func import allocate_warehouse_orders, recluster_and_reassign, mark_agent_check_in,mark_all_checked_out,calculate_earnings
from database import get_db
from table import AgentsBigPic, Warehouse,OrdersBigPic
from sqlalchemy.orm import Session
from utils import generate_orders
from sqlalchemy import and_

class OrderAllocation:
    def on_post(self, req, resp):
        """Handler to trigger allocation for all warehouses."""
        session: Session = next(get_db())
        
        warehouses_ids = [warehouse.id for warehouse in session.query(Warehouse).all()]
        
        
        for warehouse_id in warehouses_ids:

            checked_in_agents = session.query(AgentsBigPic).filter(
                AgentsBigPic.warehouse_id == warehouse_id,
                AgentsBigPic.is_checked_in == True
            ).all()
            
            if not checked_in_agents:
                print(f"No agents checked in for warehouse {warehouse_id}. Skipping allocation.")
                continue  

            print(f"Processing warehouse {warehouse_id}...")
            allocate_warehouse_orders(session, warehouse_id)
            
            agents = session.query(AgentsBigPic).filter(AgentsBigPic.warehouse_id == warehouse_id).all()
            recluster_and_reassign(session=session, agents=agents, warehouse_id=warehouse_id)
        
        resp.status = falcon.HTTP_200
        resp.media = {"message": "Order allocation has been done for all warehouses"}
        session.close()

class WorkerCheckIn:
    def on_post(self, req, resp):
        """Randomly mark agents as signed in!"""

        # Get a database session
        session: Session = next(get_db())

        # Call the function to randomly mark 80% of agents as signed in
        no_present = mark_agent_check_in(session)

        # Respond with the number of agents marked as signed in
        resp.status = falcon.HTTP_200
        resp.media = {"message": f"{no_present} agents have been randomly marked as checked in."}
        session.close()

class WorkerCheckOut:
    def on_post(self, req, resp):
        """Randomly mark agents as signed in!"""

        # Get a database session
        session: Session = next(get_db())

        # Call the function to randomly mark 80% of agents as signed in
        mark_all_checked_out(session)

        # Respond with the number of agents marked as signed in
        resp.status = falcon.HTTP_200
        resp.media = {"message": f"agents have been marked checked out."}
        session.close()

class AgentsInfo:
    def on_get(self, req, resp):
        """get agents info for the day"""

        # Get a database session
        session: Session = next(get_db())

        agents = session.query(AgentsBigPic).all()
        total_orders = 0
        total_expense = 0
        agents_info = []
        for agent in agents:
            earnings = calculate_earnings(session,agent.id)
            total_expense+=earnings
            total_orders+= agent.no_of_orders
            agents_info.append({
                "id": agent.id,
                "no_of_orders": agent.no_of_orders,
                "total_distance": agent.total_distance,
                "total_earnings": earnings,
                "is_checked_in": agent.is_checked_in,
            })
        if total_orders>0:
            cost_per_order = total_expense/total_orders
        else:
            cost_per_order = 0

        resp.status = falcon.HTTP_200
        resp.media = {"agents": agents_info,"total_no_of_orders": total_orders,"cost_per_order":cost_per_order}
        session.close()

class AgentOrders:
    def on_get(self, req, resp, agent_id):
        """get agents info for the day"""

        # Get a database session
        session: Session = next(get_db())

        orders = session.query(OrdersBigPic).filter(OrdersBigPic.assigned_agent==agent_id).all()
        
        orders_info = []
        for order in orders:
            orders_info.append({
                "id": order.id,
                "x_coord": order.x_coord,
                "y_coord": order.y_coord,
            })

        resp.status = falcon.HTTP_200
        resp.media = {"orders": orders_info}
        session.close()

class OrdersLeft:
    def on_get(self,req,resp):
        session: Session = next(get_db())

        warehouses_ids = [warehouse.id for warehouse in session.query(Warehouse).all()]

        orders_info = []
        for warehouse_id in warehouses_ids:
            orders = session.query(OrdersBigPic).filter(and_(OrdersBigPic.is_delivered==False,OrdersBigPic.warehouse_id==warehouse_id)).all()
            no_of_orders = len(orders)
            orders_info.append({
                    "warehouse_id": warehouse_id,
                    "no_of_orders": no_of_orders
                })
        

        resp.status = falcon.HTTP_200
        resp.media = {"orders": orders_info}
        session.close()

class UploadOrders:
    def on_post(self,req,resp):
        session: Session = next(get_db())

        result = generate_orders(session)

        if result == 1:  # If orders were successfully generated
            resp.status = falcon.HTTP_200
            resp.media = {"message": "Orders successfully generated and uploaded."}
        else:  # If there was an error during order generation
            resp.status = falcon.HTTP_500
            resp.media = {"message": "Failed to generate orders due to an error."}
        session.close()

app = falcon.App()

order_allocation = OrderAllocation()
worker_checkIn = WorkerCheckIn()
worker_checkOut = WorkerCheckOut()
agents_info = AgentsInfo()
agent_orders = AgentOrders()
orders_left = OrdersLeft()
upload_orders = UploadOrders()



app.add_route('/allocate/', order_allocation)
app.add_route('/checkin/',worker_checkIn)
app.add_route('/checkout/',worker_checkOut)
app.add_route('/agent_info/',agents_info)
app.add_route('/agent_orders/{agent_id}',agent_orders)
app.add_route('/orders_left/',orders_left)
app.add_route('/upload_orders/', upload_orders)