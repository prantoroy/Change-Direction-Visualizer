import os
import rasterio
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import mapping

# Function to extract urban mask within the area boundary
def extract_urban_mask(raster_path, area_geometry, urban_class=2):
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs
        if area_geometry.crs != raster_crs:
            area_geometry = gpd.GeoSeries(area_geometry).to_crs(raster_crs).geometry[0]

        shapes = [mapping(area_geometry)]
        out_image, _ = rasterio.mask.mask(src, shapes, crop=True, filled=False)
        mask = np.where(out_image[0] == urban_class, 1, 0)  # Urban = 1, Non-Urban = 0
    return mask

# Function to count urban pixels in 8 cardinal directions
def count_directions_overlay(mask_start_year, mask_end_year):
    counts_start = []
    counts_end = []
    height, width = mask_start_year.shape
    center_y, center_x = height // 2, width // 2  # Area center

    directions = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
    for dy, dx in directions:
        mask_start = np.roll(np.roll(mask_start_year, dy, axis=0), dx, axis=1)
        mask_end = np.roll(np.roll(mask_end_year, dy, axis=0), dx, axis=1)
        counts_start.append(np.sum(mask_start[center_y:, center_x:]))
        counts_end.append(np.sum(mask_end[center_y:, center_x:]))
    return counts_start, counts_end

# Function to create radar plot with percentages
def plot_direction_percentage(counts_start, counts_end, area_name, state_abbreviation, start_year, end_year):
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    angles = np.linspace(0, 2 * np.pi, len(directions), endpoint=False)

    # Calculate percentages
    total_start = sum(counts_start)
    total_end = sum(counts_end)
    perc_start = [count / total_start * 100 for count in counts_start]
    perc_end = [count / total_end * 100 for count in counts_end]

    # Plot
    fig, ax = plt.subplots(subplot_kw={"projection": "polar"}, figsize=(8, 8))
    ax.set_theta_direction(-1)  # Clockwise
    ax.set_theta_offset(np.pi / 2)  # North at top

    # Add connected lines for start and end years
    perc_start.append(perc_start[0])  # Close the loop
    perc_end.append(perc_end[0])
    angles = np.append(angles, angles[0])  # Add the first angle to close the loop

    ax.plot(angles, perc_start, color="orange", linewidth=2, label=f"Urban {start_year}", linestyle="solid")
    ax.plot(angles, perc_end, color="darkred", linewidth=2, label=f"Urban {end_year}", linestyle="solid")

    # Add annotations
    ax.set_xticks(angles[:-1])  # Exclude the duplicate last angle
    ax.set_xticklabels(directions, fontsize=12)
    ax.set_yticks(np.linspace(0, max(max(perc_start), max(perc_end)), 5))  # Scaled radial grid
    ax.set_yticklabels([f"{int(y)}%" for y in ax.get_yticks()], fontsize=10)
    ax.set_title(f"Urban Class Percentage Change\n{area_name}, {state_abbreviation}", va="bottom", fontsize=14)
    ax.legend(loc="upper right", fontsize=10)

    plt.tight_layout()
    plt.show()
