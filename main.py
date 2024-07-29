import uvicorn
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict
import pandas as pd
from gurobipy import GurobiError
from cvrp import CVRP
from tdvrp import TDVRP


app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

locations_data: List[Dict[str, float]] = []
routes_with_coordinates_T : List[List[Dict[str, float]]] = []
routes_with_coordinates_D : List[List[Dict[str, float]]] = []
df = None


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request":request})

@app.get("/generation", response_class=HTMLResponse)
def generation(request: Request):
    return templates.TemplateResponse("generation.html", {"request":request})

@app.get("/simulation", response_class=HTMLResponse)
def simulation(request: Request):
    return templates.TemplateResponse("simulation.html", {"request":request})

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    global df
    try:
        df = pd.read_csv(file.file)
        global locations_data
        locations_data = df.to_dict(orient='records')
        print(locations_data)

        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/locations", response_model=List[Dict[str, float]])
async def get_locations():
    return locations_data

@app.post("/solve")
async def solve(nDrones: str = Form(...), 
                nTrucks: str = Form(...), 
                drone_speed: str = Form(...), 
                truck_speed: str = Form(...),
                drone_capacity: str = Form(...),
                truck_capacity: str = Form(...),
                drone_autonomy: str = Form(...),
                model: str = Form(...)):
    
    tdvrp = TDVRP()
    
    df['demand'] = df['demand'].astype(int)
    demands = df['demand'].tolist()
    matrix_distance_truck = tdvrp.distance_matrix_truck(df)
    matrix_time_truck = tdvrp.time_matrix(matrix_distance_truck, float(truck_speed))
    matrix_distance_drone = tdvrp.calculate_drone_distance_matrix(df)
    matrix_time_drone = tdvrp.time_matrix(matrix_distance_drone, float(drone_speed))
    n = len(locations_data)
    customers_list = [x for x in range(1, n)]
    nodes_list = [0] + customers_list
    list_vars = []
    dic_res = dict()
    travTime = None
    runTime = None
    truck_load = None
    drone_load = None
    
    global routes_with_coordinates_T
    global routes_with_coordinates_D

    if model == "CVRP":
        cvrp = CVRP()

        resultsCVRP = cvrp.CVRP(
            df=df,
            time_truck=matrix_time_truck,
            customers=customers_list,
            nodes=nodes_list,
            nT=int(nTrucks),
            truck_capacity=int(truck_capacity))
        
        model = resultsCVRP[0]
        xt = resultsCVRP[1]
        y = resultsCVRP[2]
        dic_res[model] = (xt, y)

        routesT, routesD, travTime, runTime = cvrp.final_solving(model=model, xt=xt, y=y, dic_res=dic_res)

        orderedRoutesT = cvrp.reorder_routes(routesT)
        orderedRoutesD = cvrp.reorder_routes(routesD) if routesD else None

        routes_with_coordinates_T = cvrp.replace_indexes_with_coordinates(orderedRoutesT, df)
        routes_with_coordinates_D = cvrp.replace_indexes_with_coordinates(orderedRoutesD, df) if orderedRoutesD else None

        truck_load = sum(len(sublist) - 2 for sublist in orderedRoutesT)


        print(routes_with_coordinates_T)
        print(routes_with_coordinates_D)

        return JSONResponse(content={
                "routes_with_coordinates_T": routes_with_coordinates_T,
                "routes_with_coordinates_D": routes_with_coordinates_D,
                "running_time": runTime,
                "travel_time": travTime,
                "truck_load": truck_load,
                "drone_load": drone_load,
                "n": n
            })
        #return JSONResponse(content={"status": "success"})
    
    elif model == "TDVRP":

        resultsTDVRP = tdvrp.TDVRP(dem=demands, 
                                time_truck=matrix_time_truck, 
                                customers=customers_list, 
                                nodes=nodes_list, 
                                nT=int(nTrucks),
                                truck_capacity=int(truck_capacity),
                                nD=int(nDrones),
                                drone_capacity=int(drone_capacity),
                                drone_endurance=int(drone_autonomy),
                                time_drone=matrix_time_drone)
        
        model = resultsTDVRP[0]
        xt = resultsTDVRP[1]
        xd = resultsTDVRP[2]
        list_vars.append(xt)
        list_vars.append(xd)
        dic_res[model] = list_vars

        routesT, routesD, travTime, runTime = tdvrp.final_solving(model=model, xt=xt, xd=xd, dic_res=dic_res)
                        
        orderedRoutesT = tdvrp.reorder_routes(routesT)
        orderedRoutesD = tdvrp.reorder_routes(routesD) if routesD else None
        print(orderedRoutesT)

        routes_with_coordinates_T = tdvrp.replace_indexes_with_coordinates(orderedRoutesT, df)
        routes_with_coordinates_D = tdvrp.replace_indexes_with_coordinates(orderedRoutesD, df) if orderedRoutesD else None

        truck_load = sum(len(sublist) - 2 for sublist in orderedRoutesT)
        drone_load = sum(len(sublist) - 2 for sublist in orderedRoutesD)
 

        print(routes_with_coordinates_T)
        print(routes_with_coordinates_D)
        
        return JSONResponse(content={
                "routes_with_coordinates_T": routes_with_coordinates_T,
                "routes_with_coordinates_D": routes_with_coordinates_D,
                "running_time": runTime,
                "travel_time": travTime,
                "truck_load": truck_load,
                "drone_load": drone_load,
                "n": n
            })
        """ return JSONResponse(content={"status": "success"}) """


if __name__ == "__main__":
    uvicorn.run("main:app", port=8000, reload=True)