import streamlit as st
import os
import rasterio
from rasterio.mask import mask
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import mapping
import zipfile
import pandas as pd

# Ensure the temp directory exists
temp_dir = "temp"
os.makedirs(temp_dir, exist_ok=True)

# Paths to static files
county_names_csv_path = "County_Names.csv"
shapefile_path = "County_Bounds.zip"

# Load the CSV file for state and county names
county_names = pd.read_csv(county_names_csv_path)

# Streamlit interface
st.title("Land Cover Class Direction Analysis")
st.header("Test Version")
st.markdown(" © Bishal Roy")
st.markdown("bishal.roy@slu.edu")

# Dropdowns for State and County
state_name = st.selectbox("Select State:", options=county_names["STATE_NAME"].unique())

filtered_counties = county_names[county_names["STATE_NAME"] == state_name]
county_name = st.selectbox("Select County:", options=filtered_counties["NAME"].unique())

# Retrieve the MainID for the selected county
selected_main_id = filtered_counties[filtered_counties["NAME"] == county_name]["MainID"].values[0]

# Input for Urban Class Value
urban_class = st.number_input("Enter Land Cover Class Value:", min_value=0, value=2)

# File Uploads
uploaded_start_year = st.file_uploader("Upload Start Year Raster (TIF)", type=["tif"])
uploaded_end_year = st.file_uploader("Upload End Year Raster (TIF)", type=["tif"])

# Functions
def extract_urban_mask(raster_path, geometry, urban_class):
    with rasterio.open(raster_path) as src:
        # Ensure the geometry CRS matches the raster CRS
        raster_crs = src.crs
        geometry = gpd.GeoSeries([geometry], crs=shapefile.crs).to_crs(raster_crs).iloc[0]

        # Perform masking
        shapes = [mapping(geometry)]
        out_image, _ = mask(src, shapes, crop=True, filled=False)
        mask_array = np.where(out_image[0] == urban_class, 1, 0)
    return mask_array

def count_directions_overlay(urban_2001, urban_2019):
    counts_2001 = []
    counts_2019 = []
    height, width = urban_2001.shape
    center_y, center_x = height // 2, width // 2  # State center

    directions = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
    for dy, dx in directions:
        mask_2001 = np.roll(np.roll(urban_2001, dy, axis=0), dx, axis=1)
        mask_2019 = np.roll(np.roll(urban_2019, dy, axis=0), dx, axis=1)
        counts_2001.append(np.sum(mask_2001[center_y:, center_x:]))
        counts_2019.append(np.sum(mask_2019[center_y:, center_x:]))
    return counts_2001, counts_2019

def plot_direction_percentage(counts_start, counts_end, unit_name):
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    angles = np.linspace(0, 2 * np.pi, len(directions), endpoint=False)

    total_start = sum(counts_start)
    total_end = sum(counts_end)
    perc_start = [count / total_start * 100 for count in counts_start]
    perc_end = [count / total_end * 100 for count in counts_end]

    perc_start.append(perc_start[0])
    perc_end.append(perc_end[0])
    angles = np.append(angles, angles[0])

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(8, 8))
    ax.set_theta_direction(-1)
    ax.set_theta_offset(np.pi / 2)

    ax.plot(angles, perc_start, color="orange", linewidth=2, label="Start Year", linestyle="solid")
    ax.plot(angles, perc_end, color="darkred", linewidth=2, label="End Year", linestyle="solid")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(directions, fontsize=12)
    ax.set_yticks(np.linspace(0, max(max(perc_start), max(perc_end)), 5))  # Scaled radial grid
    ax.set_yticklabels([f"{int(y)}%" for y in ax.get_yticks()], fontsize=10)
    ax.set_title(f"Land Cover Percentage Change\n{unit_name}", va="bottom", fontsize=14)
    ax.legend(loc="upper right", fontsize=10)
    plt.text(
        0.5, -0.1,
        "change-direction.streamlit.app",
        fontsize=10,
        color="gray",
        ha="center",
        va="center",
        transform=ax.transAxes,
    )

    plot_path = "urban_direction_plot.png"
    plt.savefig(plot_path)
    plt.close()
    return plot_path

# Generate Plot
if st.button("Generate Plot"):
    if uploaded_start_year and uploaded_end_year:
        # Save uploaded files temporarily
        start_path = os.path.join(temp_dir, uploaded_start_year.name)
        end_path = os.path.join(temp_dir, uploaded_end_year.name)

        with open(start_path, "wb") as f:
            f.write(uploaded_start_year.read())
        with open(end_path, "wb") as f:
            f.write(uploaded_end_year.read())

        # Extract shapefile
        with zipfile.ZipFile(shapefile_path, "r") as zip_ref:
            zip_ref.extractall(os.path.join(temp_dir, "shapefile"))

        # Load shapefile
        shapefile = gpd.read_file(os.path.join(temp_dir, "shapefile"))

        # Filter shapefile using MainID
        filtered_shapefile = shapefile[shapefile["MainID"] == selected_main_id]

        if filtered_shapefile.empty:
            st.error(f"No matching region found for {county_name}, {state_name}.")
        else:
            state_geom = filtered_shapefile.geometry.iloc[0]

            # Extract urban masks and count directions
            urban_start = extract_urban_mask(start_path, state_geom, urban_class)
            urban_end = extract_urban_mask(end_path, state_geom, urban_class)

            counts_start, counts_end = count_directions_overlay(urban_start, urban_end)

            # Create and display plot
            plot_path = plot_direction_percentage(counts_start, counts_end, f"{county_name}, {state_name}")
            st.image(plot_path, caption="Land Cover Class Change", use_column_width=True)
    else:
        st.error("Please upload both raster files.")
