from flask import Flask, render_template, request, jsonify
import folium
from branca.element import Element
import json
import os

app = Flask(__name__)

# File path to your GeoJSON
GEOJSON_FILE = os.path.join('static', 'data', 'Charminar_afforestation_zones.geojson')
DN_TO_TEXT = {1: "Low", 2: "Moderate", 3: "High", 4: "Very High"}
DN_COLORS = {
    1: "#3498db",  # Soft Blue (Cool/Stable)
    2: "#6cfd0c",  # Bright Yellow (Warm)
    3: "#deab10",  # Vivid Orange (Hot)
    4: "#F91500"   # Deep Crimson (Critical/UHI Peak)
}

planted_trees = []

def find_zone(lat, lon):
    if os.path.exists(GEOJSON_FILE):
        with open(GEOJSON_FILE) as f:
            data = json.load(f)
        for feature in data['features']:
            geom = feature['geometry']
            # Handle both Polygon and MultiPolygon nesting
            if geom['type'] == 'Polygon':
                coords = geom['coordinates'][0]
            elif geom['type'] == 'MultiPolygon':
                coords = geom['coordinates'][0][0]
            else:
                continue

            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            
            # Bounding box check
            if min(lons) <= lon <= max(lons) and min(lats) <= lat <= max(lats):
                return feature['properties'].get('DN')
    return None

@app.route("/")
def index():
    m = folium.Map(
        location=[17.385044, 78.486671],
        zoom_start=16,
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles © Esri'
    )

    if os.path.exists(GEOJSON_FILE):
        with open(GEOJSON_FILE) as f:
            data = json.load(f)
        folium.GeoJson(
            data,
            style_function=lambda feature: {
                'fillColor': DN_COLORS.get(feature['properties'].get('DN'), 'gray'),
                'color': 'black', 'weight': 1, 'fillOpacity': 0.4
            },
            tooltip=folium.GeoJsonTooltip(fields=['DN'], aliases=['Revegetation Priority Level:'])
        ).add_to(m)

    for tree in planted_trees:
        folium.Marker([tree['lat'], tree['lon']], 
                      popup=f"<b>{tree['tree_type']}</b>",
                      icon=folium.Icon(color='green', icon='leaf')).add_to(m)

    # THE INTERNAL JS: Injected into the iframe
    click_js = """
    function onMapClick(e) {
        var lat = e.latlng.lat.toFixed(6);
        var lng = e.latlng.lng.toFixed(6);
        window.parent.document.getElementById('lat_display').value = lat;
        window.parent.document.getElementById('lon_display').value = lng;
        if (window.currentPin) { this.removeLayer(window.currentPin); }
        window.currentPin = L.marker(e.latlng).addTo(this);
        window.currentPin.bindPopup("Ready to plant here!").openPopup();
    }
    setTimeout(function(){
        var map_div = document.querySelector('.folium-map');
        var map_obj = window[map_div.id];
        map_obj.on('click', onMapClick);
    }, 500);
    """
    m.get_root().script.add_child(Element(click_js))
    return render_template("index.html", map_html=m._repr_html_())

@app.route("/plant_tree", methods=["POST"])
def plant_tree():
    try:
        data = request.get_json()
        lat, lon = float(data['lat']), float(data['lon'])
        tree_type = data['tree_type']
        zone_dn = find_zone(lat, lon)
        zone_text = DN_TO_TEXT.get(zone_dn, "General")
        planted_trees.append({"lat": lat, "lon": lon, "tree_type": tree_type, "zone": zone_text})
        return jsonify({
    "status": "success",
    "message": f"""🌱 Success! Thank You for Planting!

{tree_type} added to the {zone_text} zone mapping.

Your effort is helping to expand the green cover, reduce urban heat, and make our city—and our planet—a cooler, healthier, and more sustainable place to live. Every tree you plant contributes to a better environment for all.

Keep nurturing your plant and watch it grow—together, we’re making a real difference!"""
})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)