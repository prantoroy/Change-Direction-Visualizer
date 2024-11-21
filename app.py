import streamlit as st
import geopandas as gpd
import rasterio
from io import BytesIO
from main_code import extract_urban_mask, count_directions_overlay, plot_direction_percentage

st.title("Urban Direction Change Visualization")
st.sidebar.header("Upload Inputs")

# File Uploads
start_year_tif = st.sidebar.file_uploader("Upload Start Year Raster (TIF)", type=["tif"])
end_year_tif = st.sidebar.file_uploader("Upload End Year Raster (TIF)", type=["tif"])
shapefile = st.sidebar.file_uploader("Upload Shapefile (ZIP)", type=["zip"])

# Area Selection
unit_area_field = st.sidebar.text_input("Unit Area Field (e.g., NAME)")
unit_area_value = st.sidebar.text_input("Unit Area Value (e.g., Clark County)")
state_field = st.sidebar.text_input("State Field (e.g., STATE_ABBR)")
state_value = st.sidebar.text_input("State Value (e.g., NV)")

# Years
start_year = st.sidebar.number_input("Start Year", min_value=1900, max_value=2100, value=2001, step=1)
end_year = st.sidebar.number_input("End Year", min_value=1900, max_value=2100, value=2019, step=1)

if st.sidebar.button("Plot"):
    if not (start_year_tif and end_year_tif and shapefile):
        st.error("Please upload all required files.")
    else:
        # Extract the shapefile
        gdf = gpd.read_file("zip://" + shapefile.name)

        # Filter the shapefile for the selected area
        filtered_shapefile = gdf[
            (gdf[unit_area_field] == unit_area_value) & (gdf[state_field] == state_value)
        ]
        if filtered_shapefile.empty:
            st.error("No matching area found in the shapefile.")
        else:
            # Process and Plot
            with rasterio.open(start_year_tif) as src_start, rasterio.open(end_year_tif) as src_end:
                state_geom = filtered_shapefile.geometry.iloc[0]
                mask_start = extract_urban_mask(src_start.name, state_geom)
                mask_end = extract_urban_mask(src_end.name, state_geom)

                counts_start, counts_end = count_directions_overlay(mask_start, mask_end)
                st.pyplot(
                    plot_direction_percentage(
                        counts_start,
                        counts_end,
                        unit_area_value,
                        state_value,
                        start_year,
                        end_year,
                    )
                )
