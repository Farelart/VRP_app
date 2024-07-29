function initMap() {
    // Defining the geo coordinates of where the map will be located
    let myLatLng = {
        lat: 33.98015708073674, 
        lng: -6.731845060569447
    };

    // Defining the map options
    let mapOptions = {
        center: myLatLng,
        zoom: 16,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        disableDefaultUI: true,
        styles: [
            {
                "featureType": "all",
                "elementType": "labels.text",
                "stylers": [
                    {
                        "color": "#878787"
                    }
                ]
            },
            {
                "featureType": "all",
                "elementType": "labels.text.stroke",
                "stylers": [
                    {
                        "visibility": "off"
                    }
                ]
            },
            {
                "featureType": "landscape",
                "elementType": "all",
                "stylers": [
                    {
                        "color": "#f9f5ed"
                    }
                ]
            },
            {
                "featureType": "road.highway",
                "elementType": "all",
                "stylers": [
                    {
                        "color": "#f5f5f5"
                    }
                ]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.stroke",
                "stylers": [
                    {
                        "color": "#c9c9c9"
                    }
                ]
            },
            {
                "featureType": "water",
                "elementType": "all",
                "stylers": [
                    {
                        "color": "#aee0f4"
                    }
                ]
            }
        ]
    };

    let depot = document.getElementById("depot"); // depot element
    let depotLocation; // setting the variable of the depot's location
    let depotButton = document.getElementById("btn-depot"); // getting the depot's button id

    // create a directions service object to use the route method and get a result for our request
    let directionsService = new google.maps.DirectionsService();
    let bounds = new google.maps.LatLngBounds();
    let infoWindow = new google.maps.InfoWindow();

    // creating the map
    map = new google.maps.Map(document.getElementById("googleMap"), mapOptions);
    let geocoder = new google.maps.Geocoder(); // instanciate a geocoder object

    let dronePayloadButton = document.getElementById("btn-dronePayload");
    let truckPayloadButton = document.getElementById("btn-truckPayload");
    let dronePayload;
    let truckPayload;

    dronePayloadButton.addEventListener("click", (event) => {
        dronePayload = parseFloat(document.getElementById("dronePayload").value);
    });

    truckPayloadButton.addEventListener("click", (event) => {
        truckPayload = parseFloat(document.getElementById("truckPayload").value);
    });

    let submitTypeButton = document.getElementById("btn-submitType");
    submitTypeButton.addEventListener("click", (event) => {
        let selectedType = document.getElementById("nearByPlacesTypes").value;
        getNearByPlaces(depotLocation, selectedType);
    });

    let droneSpeedButton = document.getElementById("btn-droneSpeed");
    let droneSpeed;
    droneSpeedButton.addEventListener("click", (event) => {
        droneSpeed = parseFloat(document.getElementById("droneSpeed").value);
    })

    let moreButton = document.getElementById("more");
    moreButton.onclick = function () {
        moreButton.disabled = true;
        if (getNextPage) {
            getNextPage();
        }
    };

    let allMarkers = []; // Array to store all markers including depot
    let allDemands = []; // Array to store all demands

    // defining a function for autocompletion task
    function autocomplete() {
        let autocompleteOptions = {
            type: ['(geocode)']
        }
    
        let autocomplete = new google.maps.places.Autocomplete(depot, autocompleteOptions);
    }

    autocomplete(); // calling the autocomplete task

    // creating a function for adding markers on the map
    function addMarkers(location) {
        const marker = new google.maps.Marker({
            position: location,
            map: map,
            /* animation: goole.maps.Animation.DROP */
            icon: "/static/img/icons8-epingle-de-carte-50.png"
        });

        return marker;
    }

    // function for getting near places by specific types
    function getNearByPlaces(position, type) {
        if (!type) {
            console.error('Type is required for nearby search.');
            return;
        }

       let request = {
            location: position,
            rankBy: google.maps.places.RankBy.DISTANCE,
            // keyword: 'sushi'
            type: type,
          };
    
          service = new google.maps.places.PlacesService(map);
          service.nearbySearch(request, nearbyCallback);
    }


    function nearbyCallback(results, status, pagination) {
        if (status == google.maps.places.PlacesServiceStatus.OK) {
            totalRequests = results.length;
            if (status !== "OK" || !results) return;

            createNearByPlacesMarkers(results, map);
            moreButton.disabled = !pagination || !pagination.hasNextPage;
            if (pagination && pagination.hasNextPage) {
                getNextPage = () => {
                    // Note: nextPage will call the same handler function as the initial call
                    pagination.nextPage();
                };
            }
        }
    }

    let droneDistances = [];
    let droneDurations = [];

    let depotDemandAdded = false; // Flag to track if depot demand has been added
    // this function create the markers for near by places
    function createNearByPlacesMarkers(places, map) {
        let requests = [];
        // Add depot demand with a value of 0
        if (depotDemandAdded === false) {
            allDemands.push({ type: "depot", value: 0 });
            depotDemandAdded = true;
        }

        places.forEach(place => {
            let requestInfoWindow = {
                origin: new google.maps.LatLng(depotLocation.lat, depotLocation.lng),
                destination: place.geometry.location,
                travelMode: google.maps.TravelMode.DRIVING,
                unitSystem: google.maps.UnitSystem.METRIC
            };
    
            let marker = new google.maps.Marker({
                position: place.geometry.location,
                map: map,
                title: place.name,
                icon: "/static/img/marker.png"
            });
    
            requests.push(new Promise((resolve, reject) => {
                directionsService.route(requestInfoWindow, (result, status) => {
                    if (status == google.maps.DirectionsStatus.OK) {
                        let distance = result.routes[0].legs[0].distance.text;
                        let duration = result.routes[0].legs[0].duration.text;
                        place.distance = distance;
                        place.duration = duration;
    
                        let drone_distance = haversine_distance(depotMarker, marker).toFixed(2);
                        let drone_duration = ((drone_distance / droneSpeed) * 60).toFixed(2);
                        /* let truckPayload = null;
                        let dronePayload = null; */

                        // Generate demand based on truck and drone payloads
                        const demandType = Math.random() < 0.4 ? "drone" : "truck";
                        let demandValue;
                        if (demandType === "drone") {
                            demandValue = Math.floor(Math.random() * dronePayload) + 1; // Random between 1 and dronePayload
                        } else if (demandType === "truck") {
                            demandValue = Math.floor(Math.random() * (truckPayload - dronePayload + 1)) + dronePayload; // Random between dronePayload and truckPayload
                        }

                        place.demand = { type: demandType, value: demandValue };
                        
                        let content = `<strong>${place.name}</strong><br>Truck distance: ${place.distance}<br>Truck duration: ${place.duration}<br>Drone distance: ${drone_distance} km<br>Drone duration: ${drone_duration} min<br>Demand value: ${place.demand.value}`;
    
                        marker.addListener("mouseover", () => {
                            infoWindow.setContent(content);
                            infoWindow.open(map, marker);
                        });
    
                        resolve();
                    } else {
                        console.error('Directions service request failed due to ' + status);
                        reject(status);
                    }
                });
            }));
    
            placeLatLng = {lat: place.geometry.location.lat(), lng: place.geometry.location.lng()};
            allMarkers.push(placeLatLng);
            bounds.extend(place.geometry.location);
        });
    
        Promise.all(requests).then(() => {
            map.fitBounds(bounds);
            allDemands = allDemands.concat(places.map(place => place.demand));
            console.log(allMarkers);
            console.log(allDemands);
        }).catch((error) => {
            console.error('Failed to fetch directions:', error);
        });
    }

    // function to calcuate the drone's distance through havershine distance
    function haversine_distance(mk1, mk2) {
        let R = 6371.0710; // Radius of the Earth in kilometers(km)
        let rlat1 = mk1.position.lat() * (Math.PI/180); // Convert degrees to radians
        let rlat2 = mk2.position.lat() * (Math.PI/180); // Convert degrees to radians
        let difflat = rlat2-rlat1; // Radian difference (latitudes)
        let difflon = (mk2.position.lng()-mk1.position.lng()) * (Math.PI/180); // Radian difference (longitudes)
  
        let d = 2 * R * Math.asin(Math.sqrt(Math.sin(difflat/2)*Math.sin(difflat/2)+Math.cos(rlat1)*Math.cos(rlat2)*Math.sin(difflon/2)*Math.sin(difflon/2)));
        return d;
    }

    function haversine_distanceD(mk1, mk2) {
        let R = 6371.0710; // Radius of the Earth in kilometers(km)
        let rlat1 = mk1.lat * (Math.PI/180); // Convert degrees to radians
        let rlat2 = mk2.lat * (Math.PI/180); // Convert degrees to radians
        let difflat = rlat2-rlat1; // Radian difference (latitudes)
        let difflon = (mk2.lng-mk1.lng) * (Math.PI/180); // Radian difference (longitudes)
  
        let d = 2 * R * Math.asin(Math.sqrt(Math.sin(difflat/2)*Math.sin(difflat/2)+Math.cos(rlat1)*Math.cos(rlat2)*Math.sin(difflon/2)*Math.sin(difflon/2)));
        return d;
    }
    
    function createCircles(map, location, radius) {
        const circle = new google.maps.Circle({
            strokeColor: "#FF0000",
            strokeOpacity: 0.1,
            strokeWeight: 2,
            fillColor: "#8BC34A",
            fillOpacity: 0.2,
            map: map,
            center: location,
            radius: radius
        })
    }

    /* function generateCSV() {
        let csvContent = "lat,long,demandType,demand\n"; // Header row

        allMarkers.forEach((marker, index) => {
            let demand = allDemands[index];
            csvContent += `${marker.lat},${marker.lng},${demand.type},${demand.value}\n`;
        });

        return csvContent;
    }

    function downloadCSV() {
        let csvContent = generateCSV();
        let encodedUri = "data:text/csv;charset=utf-8," + encodeURIComponent(csvContent);
        let link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "markers.csv");
        document.body.appendChild(link);
        link.click();
    } */
    

    // geocoding the depot's address and rendering the marker on the map
    depotButton.addEventListener("click", (event) => {
        depotAddress = depot.value;
        let selectedType = document.getElementById("nearByPlacesTypes").value;
        geocoder.geocode({
            address: depotAddress
        }, (results, status) => {
            if (status == google.maps.GeocoderStatus.OK) {
                lat = results[0].geometry.location.lat();
                lng = results[0].geometry.location.lng();
                depotLocation = {lat: lat, lng: lng};
                map.setCenter(depotLocation);
                depotMarker = addMarkers(depotLocation);
                depotMarker.setAnimation(google.maps.Animation.BOUNCE);
                getNearByPlaces(depotLocation, selectedType);
                allMarkers.push(depotLocation);
            } else {
                alert('Geocode was not successful for the following reason: ' + status);
            }
        });
    });

    function generateTextFile() {
        let textContent = `NAME : test_n${allMarkers.length}_DS${droneSpeed}_DFR${droneBattery}\n`;
        textContent += `COMMENT : (GOOGLE MAPS GENERATED, Default No of trucks: 8)\n`;
        textContent += `TYPE : CVRP and TDVRP\n`;
        textContent += `DIMENSION : ${allMarkers.length}\n`;
        textContent += `EDGE_WEIGHT_TYPE : Maps directions API & Havershine\n`;
        textContent += `TRUCK_CAPACITY : ${truckPayload}\n`;
        textContent += `Drone_CAPACITY : ${dronePayload}\n`;
        textContent += `NODE_COORD_SECTION\n`;
    
        allMarkers.forEach((marker, index) => {
            textContent += `${index + 1} ${marker.lat} ${marker.lng}\n`;
        });
    
        textContent += `DEMAND_SECTION\n`;
        allDemands.forEach((demand, index) => {
            textContent += `${index + 1} ${demand.value}\n`;
        });
    
        textContent += `DEPOT_SECTION\n`;
        textContent += `1\n-1\nEOF`;
    
        return textContent;
    }

    function downloadDataFile() {
        let filename = `test_n${allMarkers.length}_DS${droneSpeed}_DFR${droneBattery}.txt`; // Example filename format
        let textContent = generateTextFile();
        let encodedUri = "data:text/plain;charset=utf-8," + encodeURIComponent(textContent);
        let link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
    }

    let downloadButton = document.getElementById("btn-notebook");
    downloadButton.addEventListener("click", downloadDataFile);

    let droneBatteryButton = document.getElementById("btn-droneBattery");
    let droneBattery;
    let droneLimit;
    droneBatteryButton.addEventListener("click", (event) => {
        droneBattery = parseFloat(document.getElementById("droneBattery").value);
        droneLimit = (((droneBattery*droneSpeed)/60)/2)*1000;
        createCircles(map, depotLocation, droneLimit);
    });

    /* let dronePayloadButton = document.getElementById("btn-dronePayload");
    let truckPayloadButton = document.getElementById("btn-truckPayload");
    let dronePayload;
    let truckPayload;

    dronePayloadButton.addEventListener("click", (event) => {
        dronePayload = parseFloat(document.getElementById("dronePayload").value);
    });

    truckPayloadButton.addEventListener("click", (event) => {
        truckPayload = parseFloat(document.getElementById("truckPayload").value);
    }); */
    
    let dis = document.getElementById("dis");
    dis.addEventListener("click", (event) => {
        let distance;
        let duration;
        let distances = [];
        let durations = [];
        let totalDistancesCalculated = 0; // Initialize the counter
        let i = 0;
        let j = 0;

        function calculateDistance() {
            if (i < allMarkers.length) {
                let requestInfoWindow = {
                    origin: new google.maps.LatLng(allMarkers[i].lat, allMarkers[i].lng),
                    destination: new google.maps.LatLng(allMarkers[j].lat, allMarkers[j].lng),
                    travelMode: google.maps.TravelMode.DRIVING,
                    unitSystem: google.maps.UnitSystem.METRIC
                };

                directionsService.route(requestInfoWindow, (result, status) => {
                    if (status == google.maps.DirectionsStatus.OK) {
                        if(i===j) {
                            distance = 0;
                            duration = 0;
                        } else {
                            distance = result.routes[0].legs[0].distance.value;
                            duration = result.routes[0].legs[0].duration.value;
                        }
                        if (!distances[i]) distances[i] = [];
                        if (!durations[i]) durations[i] = [];
                        distances[i][j] = distance;
                        durations[i][j] = duration;
                        console.log(`Distance from marker ${i} to marker ${j}: ${distance}`);
                        totalDistancesCalculated++; // Increment the counter
                    } else {
                        console.error('Directions service request failed due to ' + status);
                    }

                    // Move to the next marker pair
                    j++;
                    if (j >= allMarkers.length) {
                        j = 0;
                        i++;
                    }

                    // Calculate distance for the next pair
                    calculateDistance();
                });
            } else {
                // All distances have been calculated
                console.log("All distances calculated");
                console.log("Total distances calculated:", totalDistancesCalculated);

                // Convert distances and durations to string
                let distancesString = distances.map(row => row.join(',')).join('\n');
                let durationsString = durations.map(row => row.join(',')).join('\n');

                // Download distances and durations as text files
                downloadTextFile(distancesString, 'truck_distances.txt');
                downloadTextFile(durationsString, 'truck_time_matrix.txt');
            }
        }

        // Start the recursive function
        calculateDistance();    
        // Callback function used to process Distance Matrix response
        function calculateDroneDistance() {
            for (let i = 0; i < allMarkers.length; i++) {
                // Initialize empty arrays to store distances and durations from marker i to all other markers
                let distancesFromMarkerI = [];
                let durationsFromMarkerI = [];
            
                for (let j = 0; j < allMarkers.length; j++) {
                    // Calculate the distance between marker i and marker j
                    let distance = parseInt(haversine_distanceD(allMarkers[i], allMarkers[j])*1000);
            
                    // Add the distance to the array
                    distancesFromMarkerI.push(distance);
            
                    // Calculate the drone duration based on the distance
                    let droneDuration = parseInt(calculateDroneDuration(distance));
            
                    // Add the drone duration to the array
                    durationsFromMarkerI.push(droneDuration);
                }
                
                // Add the arrays of distances and durations from marker i to droneDistances and droneDurations respectively
                droneDistances.push(distancesFromMarkerI);
                droneDurations.push(durationsFromMarkerI);
            }

            let droneDistancesString = droneDistances.map(row => row.join(',')).join('\n');
            let droneDurationsString = droneDurations.map(row => row.join(',')).join('\n');
            downloadTextFile(droneDistancesString, 'drone_distances.txt');
            downloadTextFile(droneDurationsString, 'drone_durations.txt');
        }

        calculateDroneDistance();
          
    });

    function downloadTextFile(text, filename) {
        // Create a Blob object from the text content
        let blob = new Blob([text], { type: 'text/plain' });

        // Create a temporary URL for the Blob
        let url = window.URL.createObjectURL(blob);

        // Create a link element
        let link = document.createElement('a');

        // Set the link's attributes
        link.href = url;
        link.download = filename;

        // Append the link to the document body
        document.body.appendChild(link);

        // Programmatically click the link to trigger the download
        link.click();

        // Cleanup: remove the link and revoke the URL
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    }

    function calculateDroneDuration(droneDistance) {
        // Calculate drone duration in minutes
        return (droneDistance / (droneSpeed/3.6)).toFixed(2);
    }

    document.getElementById('btn-downloadCSV').addEventListener('click', function() {
        downloadCSV(allMarkers,allDemands);
    });
    
    function downloadCSV(allMarkers,allDemands) {
        let csvContent = "lat,long,demand\n"; // Header row
    
        allMarkers.forEach((marker, index) => {
            const demand = allDemands[index] ? allDemands[index].value : 0; // Ensure the demand value is set
            csvContent += `${marker.lat},${marker.lng},${demand}\n`;
        });
    
        // Create a blob object from the CSV content
        let blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        let link = document.createElement("a");
        
        if (link.download !== undefined) { // feature detection
            // Browsers that support HTML5 download attribute
            let url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", "markers.csv");
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
    
}



