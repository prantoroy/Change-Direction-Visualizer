import streamlit as st
import os
import rasterio
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import mapping

# Function to extract urban mask within the shapefile boundary
def extract_urban_mask(raster_path, geometry, urban_class=2):
    with rasterio.open(raster_path) as src:
        shapes = [mapping(geometry)]
        out_image, _ = rasterio.mask.mask(src, shapes, crop=True, filled=False)
        mask = np.where(out_image[0] == urban_class, 1, 0)
    return mask

# Function to count urban pixels in 8 directions
def count_directions(urban_mask):
    height, width = urban_mask.shape
    center_y, center_x = height // 2, width // 2
    directions = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
    counts = [np.sum(np.roll(np.roll(urban_mask, dy, axis=0), dx, axis=1)) for dy, dx in directions]
    return counts

# Function to create radar plot
def plot_direction(counts_2001, counts_2019, unit_name):
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    angles = np.linspace(0, 2 * np.pi, len(directions), endpoint=False)

    total_2001 = sum(counts_2001)
    total_2019 = sum(counts_2019)
    perc_2001 = [count / total_2001 * 100 for count in counts_2001]
    perc_2019 = [count / total_2019 * 100 for count in counts_2019]

    perc_2001.append(perc_2001[0])
    perc_2019.append(perc_2019[0])
    angles = np.append(angles, angles[0])

    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(8, 8))
    ax.set_theta_direction(-1)
    ax.set_theta_offset(np.pi / 2)

    ax.plot(angles, perc_2001, label="Start Year", color="orange", linestyle="solid")
    ax.plot(angles, perc_2019, label="End Year", color="darkred", linestyle="solid")

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(directions, fontsize=12)
    ax.set_title(f"Urban Class Change\n{unit_name}", va="bottom", fontsize=14)
    ax.legend(loc="upper right", fontsize=10)

    plot_path = "urban_direction_plot.png"
    plt.savefig(plot_path)
    plt.close()
    return plot_path

# Streamlit interface
st.title("Urban Class Direction Analysis")

uploaded_start_year = st.file_uploader("Upload Start Year Raster (TIF)", type=["tif"])
uploaded_end_year = st.file_uploader("Upload End Year Raster (TIF)", type=["tif"])
uploaded_shapefile = st.file_uploader("Upload Shapefile (ZIP - All Shapefile Parts)", type=["zip"])

unit_area_field = st.text_input("Unit Area Field (e.g., NAME):", "")
unit_area_value = st.text_input("Unit Area Value (e.g., County Name):", "")
state_field = st.text_input("State Field (e.g., STATE_ABBR):", "")
state_value = st.text_input("State Value (e.g., State Abbreviation):", "")

if st.button("Generate Plot"):
    if uploaded_start_year and uploaded_end_year and uploaded_shapefile:
        # Save uploaded files temporarily
        start_path = os.path.join("temp", uploaded_start_year.name)
        end_path = os.path.join("temp", uploaded_end_year.name)
        shapefile_path = os.path.join("temp", "shapefile.zip")

        with open(start_path, "wb") as f:
            f.write(uploaded_start_year.read())
        with open(end_path, "wb") as f:
            f.write(uploaded_end_year.read())
        with open(shapefile_path, "wb") as f:
            f.write(uploaded_shapefile.read())

        # Extract shapefile
        import zipfile
        with zipfile.ZipFile(shapefile_path, "r") as zip_ref:
            zip_ref.extractall("temp/shapefile")

        # Load shapefile and filter
        shapefile = gpd.read_file("temp/shapefile")
        filtered_shapefile = shapefile[
            (shapefile[unit_area_field] == unit_area_value) & (shapefile[state_field] == state_value)
        ]

        if filtered_shapefile.empty:
            st.error(f"No matching region found for {unit_area_value}, {state_value}.")
        else:
            state_geom = filtered_shapefile.geometry.iloc[0]

            # Extract urban masks and count directions
            urban_2001 = extract_urban_mask(start_path, state_geom)
            urban_2019 = extract_urban_mask(end_path, state_geom)

            counts_2001 = count_directions(urban_2001)
            counts_2019 = count_directions(urban_2019)

            # Create and display plot
            plot_path = plot_direction(counts_2001, counts_2019, unit_area_value)
            st.image(plot_path, caption="Urban Class Change", use_column_width=True)
    else:
        st.error("Please upload all required files.")