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
    };

    // creating the map
    map = new google.maps.Map(document.getElementById("map"), mapOptions);
}