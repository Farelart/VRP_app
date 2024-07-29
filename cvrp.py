import numpy as np
import matplotlib.pyplot as plt
import gurobipy as grb
from gurobipy import Model, GRB, quicksum, GurobiError
import pandas as pd
import googlemaps
import itertools
import seaborn as sns
import matplotlib.colors as colors
from scipy.spatial import distance
import math


class CVRP:
    def __init__(self) -> None:
        pass

    def distance_matrix_truck(self, data):
        data_array =data[['lat','long']].to_numpy()
        travel_distance = distance.cdist(data_array, data_array, metric='euclidean')
        travel_distance = travel_distance*100000

        return travel_distance.tolist()
    
    def time_matrix(self, distance_matrix, speed):
        time_matrix = np.zeros_like(distance_matrix)
        for i in range(len(distance_matrix)):
            for j in range(len(distance_matrix)):
                distance = distance_matrix[i][j]
                time_matrix[i][j] = distance / speed
                
        return time_matrix
    
    def calculate_average_speed(self, distance_matrix, time_matrix):
        total_distance = 0
        total_time = 0

        for i in range(len(distance_matrix)):
            for j in range(len(distance_matrix[i])):
                total_distance += distance_matrix[i][j]
                total_time += time_matrix[i][j]

        average_speed = total_distance / total_time

        return average_speed
    

    def CVRP(self, df, time_truck, customers, nodes, nT, truck_capacity):
        #def CVRP(df,time_truck,customers, nodes, n_trucks, truck_capacity):
        mdl = Model('CVRP2')
        arc_k = {(i, j) for i in nodes for j in nodes if i != j}
        var = {(i) for i in customers}
        xt = mdl.addVars(arc_k, vtype=GRB.BINARY, name='xt')
        y =  mdl.addVars(var, vtype=GRB.CONTINUOUS, lb=0, ub=truck_capacity, name='y')
        mdl.modelSense = GRB.MINIMIZE
        mdl.setObjective(grb.quicksum(time_truck[i][j] * xt[i, j] if i!=j else 0 for i in nodes for j in nodes)) 
        #Constraint 1- Exactly the total number of vehicles leaves the depot and assigned to a route
        mdl.addConstr(grb.quicksum(xt[0, j] for j in customers) <= nT, name='C1')
        # Constraint 2- Customer is only served once by only one vehicle
        for j in customers:
            mdl.addConstr(grb.quicksum(xt[i, j] for i in nodes if i != j) == 1, name='C2')
        mdl.addConstr(grb.quicksum(xt[i, 0] for i in customers) <= nT, name='C3')
        # Constraint 5- Only one vehicle enters and leaves each customer location (net flow)
        for j in customers:
            mdl.addConstr(grb.quicksum(xt[i, j] if i != j else 0 for i in nodes) 
                        - grb.quicksum(xt[j, i] if i != j else 0 for i in nodes) == 0, name='C4')
        # Constraint 6: Subtour Elimination
        for i in customers:
            for j in customers:
                if i != j:
                    mdl.addConstr(y[j] <= y[i] - df.demand[i] * xt[i,j] + truck_capacity * (1 - xt[i, j]) , name= 'C5')
    #     #Constraint 7: Capacity Bounding Constraint
        for i in customers:
            mdl.addConstr(y[i] >= df.demand[i], name= 'C6')
            mdl.addConstr(y[i] <= truck_capacity, name = 'C7')
        return mdl, xt, y
    
    def solving_model(self, mdl):
        mdl.Params.TimeLimit = 3600
        mdl.Params.PreSparsify=-1 
        mdl.Params.Cuts=0
        mdl.Params.MIPFocus=1
        solution = mdl.optimize()
        runTime = mdl.Runtime
        status = mdl.status
        travelTime = 0
        # Check the status and print the results
        if status == grb.GRB.OPTIMAL:
            #print('Optimal Solution Found')
            #print('Trucks:', trucks)
            travelTime = mdl.objVal
            print('Optimal Travel Time:', travelTime)
            print('Running Time:', runTime)
        else:
            print('No optimal solution found')
        
        return status, runTime, travelTime
    

    def extract_routes(self, active_arcs):
        routes = {}
        l=0
        for (i,j) in active_arcs:
            V = []
            l =l+1
            t = (i,j)
            if routes:
                rlist = [i for i in routes.values()]
                frlist = [item for sublist in rlist for item in sublist]
                res= [item for item in frlist if item[0] == j and j!=0]
                res1 =  [item for item in frlist if item[1] == i and i!=0]
                if res and res1:
                    L = res+res1
                    k =[k for k,v in routes.items() for l in L if l in v]
                    LL = list(set(k))
                    M= np.min(LL)
                    LL.remove(M)
                    for k in LL:
                        routes[M] = routes[M]+routes[k]
                        val = routes[M]
                        val.append(t)
                        del routes[k]
                if res and not res1:
                    k =[k for k,v in routes.items() for l in res if l in v]
                    val = routes[k[0]] 
                    val.append(t)
                elif res1 and not res:
                    k =[k for k,v in routes.items() for l in res1 if l in v]
                    val = routes[k[0]] 
                    val.append(t)
                elif not res1 and not res:
                    V.append(t)
                    routes[l-1] = V
            else:
                V.append(t)
                routes[l-1] = V

        return routes
    
    def final_solving(self, model, xt, y, dic_res):
        numIter = 1
        for mdl in dic_res:
            vars = []
            routesT = []
            routesD= []
            print("===================model==========:", mdl)
            name = mdl.ModelName
            vars = dic_res[mdl]
            xt = vars[0]
            y = vars[1]
            runTimeTot = 0
            for i in range(1, numIter+1):
                res = self.solving_model(mdl)
                status = res[0]
                runTime = res[1]
                TravTime = res[2]
                runTimeTot = runTimeTot + runTime
                runTimeAvg = runTimeTot/numIter
            print("run time average CVRP: ", runTimeAvg)
            print("Travel Time ", TravTime)
            if status == 2:
                mdl.write("modelCVRP2F.lp")
                #plot_solution_WV(nodes,mdl, data, xt, xd)
                vals_t = mdl.getAttr('X', xt)
                arcs_t = [(i,j) for i, j in vals_t.keys() if vals_t[i, j] > 0.99]
            #print("**************************arcs_t********************************", arcs_t)
                routesT = self.extract_routes(arcs_t)
                routesD = None
                print("**************************routesT********************************", routesT)
            else:
                try:
                    mdl.computeIIS()
                    mdl.write('iismodelCVRP2F.ilp')
                    mdl.write("modelCVRP2F.lp")
                except GurobiError as e:
                    if "Cannot compute IIS on a feasible model" in str(e):
                        print("Model is feasible, no IIS found.")
                    else:
                        raise e
        
        return routesT, routesD, TravTime, runTimeAvg
    

    def reorder_routes(self, routes):
        new_routes = []
        for key, route in routes.items():
            current_node = 0
            new_route = [current_node]
            
            while True:
                next_node = None
                for pair in route:
                    if pair[0] == current_node:
                        next_node = pair[1]
                        break
                if next_node is None or next_node == 0:
                    new_route.append(0)
                    break
                new_route.append(next_node)
                current_node = next_node

            new_routes.append(new_route)

        return new_routes
    

    def replace_indexes_with_coordinates(self, ordered_routes, df):
        routes_with_coordinates = []
        for route in ordered_routes:
            route_with_coords = [{"lat": df.iloc[index]['lat'], "lng": df.iloc[index]['long']} for index in route]
            routes_with_coordinates.append(route_with_coords)
        return routes_with_coordinates