from ortools.constraint_solver import pywrapcp, routing_enums_pb2
import math
from table import Warehouse,OrdersBigPic
from random import uniform

def dist_between_points(x1,y1,x2,y2):
    return math.sqrt((x1-x2)**2 + (y2-y1)**2)

def solve_tsp(distance_matrix):
    # Create the routing index manager
    manager = pywrapcp.RoutingIndexManager(len(distance_matrix), 1, 0)

    # Create Routing Model
    routing = pywrapcp.RoutingModel(manager)

    # Define cost of each edge (distance)
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(distance_matrix[from_node][to_node])  # Ensure it's an integer

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Define search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    # Solve the problem
    solution = routing.SolveWithParameters(search_parameters)

    # Check if a solution was found
    if solution:
        route = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            # print(f"Visiting node {node_index}")  # Debugging print to track route
            route.append(node_index)
            index = solution.Value(routing.NextVar(index))
        route.append(manager.IndexToNode(index))  # Return to start
        print("tsp_complete")
        return route
    else:
        print("No solution found!")
        return None

def generate_orders(session):
    try:
        warehouse_info = session.query(Warehouse).all()
        for warehouse in warehouse_info:
            for i in range(1200):
                wh_id = warehouse.id
                wh_x = warehouse.x_coord
                wh_y = warehouse.y_coord
                x = round(uniform(wh_x-40,wh_x+40),2)
                y = round(uniform(wh_y-40,wh_y+40),2)
                order_dict = {"warehouse_id":wh_id,"x_coord":x,"y_coord":y}
                order_ob = OrdersBigPic(**order_dict)
                session.add(order_ob)
            session.commit()
        return 1
    except Exception as e:
        session.rollback()  
        print(f"Error generating orders: {e}")  
        return 0  