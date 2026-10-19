"""Interactive India map + alert subscription box (Tab 1, left column)."""
import streamlit as st
import folium
from streamlit_folium import st_folium

from api_client import fetch_stations, call_geo_match, subscribe_alert

DARK_TILES_URL = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
DARK_TILES_ATTR = "Esri, HERE, Garmin, &copy; OpenStreetMap contributors, GIS User Community"


def render_map_panel():
    st.markdown("### 📍 Select Location on India Map")
    st.caption("Click anywhere on the map of India to auto-fill weather parameters from the nearest meteorological station.")

    stations = fetch_stations()

    m = folium.Map(
        location=[st.session_state.selected_lat, st.session_state.selected_lon],
        zoom_start=5,
        min_zoom=4,
        max_zoom=12,
        max_bounds=True,
        min_lat=6.0,
        max_lat=38.0,
        min_lon=68.0,
        max_lon=98.0,
        tiles=DARK_TILES_URL,
        attr=DARK_TILES_ATTR
    )

    for stn in stations[::2]:
        s_lat = stn.get('latitude')
        s_lon = stn.get('longitude')
        s_name = stn.get('station_name')
        s_rain = stn.get('rainfall', 0.0)

        folium.CircleMarker(
            location=[s_lat, s_lon],
            radius=3,
            color="#0284C7",
            fill=True,
            fill_color="#38BDF8",
            fill_opacity=0.6,
            tooltip=f"Station: {s_name} (Normal: {s_rain:.1f} mm/day)"
        ).add_to(m)

    folium.Marker(
        location=[st.session_state.selected_lat, st.session_state.selected_lon],
        popup="Selected Target Location",
        icon=folium.Icon(color="red" if (st.session_state.prediction_result and st.session_state.prediction_result.get('prediction') == 1) else "blue", icon="cloud-rain", prefix="fa")
    ).add_to(m)

    map_data = st_folium(m, width="100%", height=520, key="india_folium_map")

    if map_data and map_data.get("last_clicked"):
        click_lat = round(map_data["last_clicked"]["lat"], 4)
        click_lon = round(map_data["last_clicked"]["lng"], 4)

        if 6.0 <= click_lat <= 38.0 and 68.0 <= click_lon <= 98.0:
            if click_lat != st.session_state.selected_lat or click_lon != st.session_state.selected_lon:
                st.session_state.selected_lat = click_lat
                st.session_state.selected_lon = click_lon
                st.session_state.matched_data = call_geo_match(click_lat, click_lon)
                st.session_state.prediction_result = None
                st.rerun()

    if st.session_state.matched_data is None:
        st.session_state.matched_data = call_geo_match(st.session_state.selected_lat, st.session_state.selected_lon)

    matched = st.session_state.matched_data or {}
    st.markdown(f"""
    <div class="info-callout">
        <strong>📍 Nearest IMD Station:</strong> {matched.get('matched_station', 'Unknown')} ({matched.get('matched_state', '')}) &nbsp;|&nbsp;
        <strong>Distance:</strong> {matched.get('distance_km', 0.0)} km &nbsp;|&nbsp;
        <strong>Elevation:</strong> {matched.get('elevation', 0)} m
        <br><small style="color: #94A3B8;">Spatial index matched using Haversine BallTree over 406 stations.</small>
    </div>
    """, unsafe_allow_html=True)

    # Automated Risk Alert Subscription Box (Required Feature #2)
    with st.expander("🔔 Subscribe for Automated Heavy Rain Email Alerts for this Region"):
        sub_email = st.text_input("Enter Email Address", key="sub_email_input", placeholder="user@example.com")
        if st.button("Subscribe to Alerts", type="secondary", width='stretch'):
            if sub_email and "@" in sub_email:
                success, message = subscribe_alert(
                    sub_email,
                    matched.get("matched_station", "Target Region"),
                    st.session_state.selected_lat,
                    st.session_state.selected_lon
                )
                if success:
                    st.success(message)
                else:
                    st.error(message)
            else:
                st.warning("Please enter a valid email address.")
