import numpy as np
import matplotlib.pyplot as plt
import gurobipy as grb
from gurobipy import Model, GRB, quicksum, GurobiError
import pandas as pd
import googlemaps
from haversine import haversine, Unit
import itertools
import seaborn as sns
import matplotlib.colors as colors
from scipy.spatial import distance
import os
import math


class TDVRP:
    def __init__(self) -> None:
        pass

    def distance_matrix_truck(self, data):
        data_array =data[['lat','long']].to_numpy()
        travel_distance = distance.cdist(data_array, data_array, metric='euclidean')
        travel_distance = travel_distance*100000

        return travel_distance.tolist()
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        # Convert latitude and longitude from degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        # Radius of the Earth in kilometers (you can use 3956 miles for distance in miles)
        R = 6371
        # Calculate the distance
        distance = R * c

        return distance
    
    def calculate_drone_distance_matrix(self, data):
        locations = data[['lat', 'long']].values.tolist()

        drone_distance_matrix = []
        for i, origin in enumerate(locations):
            lat1, lon1 = origin
            row = []
            for j, destination in enumerate(locations):
                lat2, lon2 = destination
                distance = int(self.haversine_distance(lat1, lon1, lat2, lon2) * 1000)
                row.append(distance)
            drone_distance_matrix.append(row)
        return drone_distance_matrix
    
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
    
    def calculate_average_ratio(self, truck_time_matrix, drone_time_matrix):
        total_ratio = 0
        num_elements = 0

        for i in range(len(truck_time_matrix)):
            for j in range(len(truck_time_matrix[i])):
                truck_time = truck_time_matrix[i][j]
                drone_time = drone_time_matrix[i][j]

                if truck_time != 0 and drone_time != 0:  # Exclude zero values to avoid division by zero
                    ratio = truck_time / drone_time
                    total_ratio += ratio
                    num_elements += 1

        average_ratio = total_ratio / num_elements

        return average_ratio

    def TDVRP(self, dem, time_truck, customers, nodes, nT, truck_capacity, nD, drone_capacity, drone_endurance, time_drone):
        mdl = Model('TDVRP2')
        #---------------------------------------------------------
        arc_k = {(i, j) for i in nodes for j in nodes if i != j}
        var = {(i) for i in customers}
        #---------------------------------------------------------
        xt = mdl.addVars(arc_k, vtype=GRB.BINARY, name='xt')
        xd = mdl.addVars(arc_k, vtype=GRB.BINARY, name='xd')
        y = mdl.addVars(var, vtype=GRB.CONTINUOUS, lb=0, ub=truck_capacity, name='y')
        w = mdl.addVars(var,vtype=GRB.BINARY, name='w')
        #------------------------------------------------------------------
        mdl.modelSense = GRB.MINIMIZE
        mdl.setObjective(grb.quicksum(time_truck[i][j] * xt[i, j] if i!=j else 0 for i in nodes 
                        for j in nodes) + grb.quicksum(time_drone[i][j] * xd[i, j] if i!=j else 0 for i in nodes for j in nodes))
        #---------------------------------------------------------
        mdl.addConstr(grb.quicksum(xt[0, j] for j in customers)  <= nT, name='C11')
        mdl.addConstr(grb.quicksum(xd[0, j] for j in customers)  <= nD, name='C12')

        mdl.addConstr(grb.quicksum(xt[i, 0] for i in customers) <= nT, name='C21')
        mdl.addConstr(grb.quicksum(xd[i, 0] for i in customers) <= nD, name='C22')
        for j in customers:
                mdl.addConstr(grb.quicksum(xt[i, j] for i in nodes if i != j) 
                            + grb.quicksum(xd[i, j] for i in nodes if i != j) == 1, name='C3')
        for j in customers:
            mdl.addConstr(grb.quicksum(xt[i, j] if i != j else 0 for i in nodes) 
                        - (grb.quicksum(xt[j, i] if i != j else 0 for i in nodes)) == 0, name = 'C4') 
        #-------------------------------------------------------------------------------  
        for j in customers:
            mdl.addConstr(grb.quicksum(xd[i, j] if i != j else 0 for i in nodes) 
                        - (grb.quicksum(xd[j, i] if i != j else 0 for i in nodes)) == 0, name = 'C5') 
        #------------------------------------------------------------------------    
        mdl.addConstr(grb.quicksum(time_drone[i][j] * xd[i, j] if i != j else 0 for i in nodes 
                                for j in nodes) <= drone_endurance, name='C6')
        for i in customers:
            for j in customers:
                if i != j:  
                    mdl.addConstr(y[j] <= y[i] - dem[j]* (xt[i,j] + xd[i,j]) + 100000 * (1- (xt[i, j]+xd[i,j])) , name= 'C7')
        for i in customers:
            mdl.addConstr(y[i] <= (drone_capacity - dem[i])*(grb.quicksum(xd[j,i] if i != j else 0 for j in nodes)) 
                                + (truck_capacity - dem[i])*(grb.quicksum(xt[j,i] if i != j else 0 for j in nodes)), name = 'C9')

        for i in customers:
            mdl.addConstr(dem[i] <= drone_capacity*w[i] + 1000 * (1-w[i]), name ='C12')
            mdl.addConstr(drone_capacity * (1-w[i]) <= dem[i],  name = 'C13')
            mdl.addConstr(grb.quicksum(xd[j,i] if i != j else 0 for j in nodes) <= drone_capacity*w[i], name = 'C14')
        
        return mdl, xt, xd
    

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
    

    def final_solving(self, model, xt, xd, dic_res):
        numIter = 1
        for mdl in dic_res:
            vars = []
            routesT = []
            routesD= []
            print("===================model==========:", mdl)
            name = mdl.ModelName
            vars = dic_res[mdl]
            xt = vars[0]
            xd = vars[1]
            runTimeTot = 0
            for i in range(1, numIter+1):
                res = self.solving_model(mdl)
                status = res[0]
                runTime = res[1]
                TravTime = res[2]
                #TravTime = 2*sum(time_truck[0]) + 2*sum(time_drone[0])- savCost
                runTimeTot = runTimeTot + runTime
                runTimeAvg = runTimeTot/numIter
                if TravTime ==0:
                    break
                print("run time average TDVRP: ", runTimeAvg)
                print("Travel time ", TravTime)
                #print("Travel Time ", TravTime)
                mdl.write("modelTDVRP2F.lp")
                if status == 2:
                    mdl.write("modelTDVRP2F.lp")
                    all_vars = mdl.getVars()
                    values = mdl.getAttr("X", all_vars)
                    names = mdl.getAttr("VarName", all_vars)
    #                 for name, val in zip(names, values):
    #                     print(f"{name} = {val}")
    #                         plot_solution_WV(nodes,mdl, df, xt, xd)
                    vals_t = mdl.getAttr('X', xt)
                    arcs_t = [(i,j) for i, j in vals_t.keys() if vals_t[i, j] > 0.99]
                    routesT = self.extract_routes(arcs_t)
                    vals_d = mdl.getAttr('X', xd)
                    arcs_d = [(i,j) for i, j in vals_d.keys() if vals_d[i, j] > 0.99]
                    print("**************************arcsT********************************", arcs_t)
                    print("**************arcD ",arcs_d)
                    routesT = self.extract_routes(arcs_t)
                    routesD = self.extract_routes(arcs_d)
                    print("**************************routesT********************************", routesT)
                    print("*********************routesD", routesD)
                else:
                    try:
                        mdl.computeIIS()
                        mdl.write('iismodelTDVRP2F.ilp')
                        print('\nThe following constraints and variables are in the IIS:')
                        for c in mdl.getConstrs():
                            if c.IISConstr: print(f'\t{c.constrname}: {mdl.getRow(c)} {c.Sense} {c.RHS}')

                        for v in mdl.getVars():
                            if v.IISLB: print(f'\t{v.varname} ≥ {v.LB}')
                            if v.IISUB: print(f'\t{v.varname} ≤ {v.UB}')
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