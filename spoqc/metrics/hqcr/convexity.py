from spoqc.reporting import plots_enabled

import numpy as np
import plotly.express as px
import geopandas as gpd

from typing import Tuple, List

from ... import helperfuncs
from ... import core

def _is_convex(polygon: List[Tuple[float, float]]) -> Tuple[bool, float]:
    """
    Determines if a polygon is convex and measures its convexity.
    
    Parameters:
        polygon (List[Tuple[float, float]]): List of (x, y) vertices defining the polygon.
        
    Returns:
        Tuple[bool, float]: 
            - A boolean indicating whether the polygon is convex.
            - A float representing the convexity metric (range [0, 1]; 1 is fully convex).
    """
    n = len(polygon)
    if n < 3:
        raise ValueError("A polygon must have at least three vertices.")
    
    coordinates = np.asarray(polygon)
    edges = np.roll(coordinates, -1, axis=0) - coordinates
    next_edges = np.roll(edges, -1, axis=0)
    cross_products = edges[:, 0] * next_edges[:, 1] - edges[:, 1] * next_edges[:, 0]

    positive = np.count_nonzero(cross_products > 0)
    negative = np.count_nonzero(cross_products < 0)
    consistent = max(positive, negative)
    return consistent == n, consistent / n


# Function to assign nulcei to cell
def _find_overlapping_nuclei(cells: gpd.GeoDataFrame, nucleus: gpd.GeoDataFrame):
    print("[NOTE] Find overlapping nuceli for cells")
    timer = helperfuncs.Timer()
    timer.start()
    overlaps = []
    nucleus_centroids = nucleus.geometry.centroid
    for cell in cells.geometry:
        overlapping_indices = nucleus[nucleus_centroids.geometry.intersects(cell)].index.tolist()
        overlaps.append(overlapping_indices)
    timer.stop()
    return overlaps


def _calc_convexity(sdata, figure_path):

    timer = helperfuncs.Timer()

    # Convexity calculation for cell polygon
    print("[NOTE] Calculate convexity for cells")
    timer.start()
    cell_convexity_metric_list = []
    for poly in sdata['cell_boundaries']['geometry']:
        # [:-1] because starting point is in the poly twice, so we have to remove it once, 
        # else we produce two zero cross products.
        cell_is_polygon_convex, cell_convexity_metric = _is_convex(list(poly.exterior.coords)[:-1])
        cell_convexity_metric_list.append(cell_convexity_metric)
    timer.stop()

    sdata['table'].obs['convexity_cell'] = [True if x > 0.5 else False for x in cell_convexity_metric_list]
    sdata['table'].obs['convexity_metric_cell'] = cell_convexity_metric_list

    # Find nuceli cell overlaps
    nulcei_of_the_cell = _find_overlapping_nuclei(sdata['cell_boundaries'], sdata['nucleus_boundaries'])
    sdata['table'].obs['nuclei_idxs'] = nulcei_of_the_cell

    # Convexity calcualteion for nuclei associated with cell
    print("[NOTE] Calculate convexity for cells")
    timer.start()
    nulcei_convexity_metric_list = []
    min_convexity_metric_list = []
    nuclei_idxs = sdata['table'].obs['nuclei_idxs']
    for cell_nuclei in nuclei_idxs:
            if ( len(cell_nuclei) != 0 ):
                # Since we might have more then one nuclei in a cell we take the mean.
                convexities = []
                for nuceuls_idx in cell_nuclei:
                    nuceuls_poly = sdata['nucleus_boundaries']['geometry'].loc[nuceuls_idx]
                    # [:-1] because starting point is in the poly twice, so we have to remove it once, 
                    # else we produce two zero cross products.
                    is_polygon_convex, convexity_metric = _is_convex(list(nuceuls_poly.exterior.coords)[:-1])
                    convexities.append(convexity_metric)
                nulcei_convexity_metric_list.append(np.mean(convexities))
                min_convexity_metric_list.append(np.min(convexities))
            else:
                nulcei_convexity_metric_list.append(0)
                min_convexity_metric_list.append(0)
    timer.stop()

    sdata['table'].obs['convexity_mean_nuceli'] = nulcei_convexity_metric_list
    sdata['table'].obs['convexity_min_nuceli'] = min_convexity_metric_list
    sdata['table'].obs['convexity_nuclei'] = [True if x > 0.5 else False for x in min_convexity_metric_list]

    if plots_enabled():
        plotcats = [['convexity_cell', 'convexity_metric_cell'],
                    ['convexity_nuclei', 'convexity_mean_nuceli']]

        figures = []
        for i, cat in enumerate(plotcats):

            helperfuncs.plot_scatter(sdata['table'], figure_path, cat[0], None,
                                    cat[0], ['black', 'lightblue'], None)
            helperfuncs.plot_scatter_density(sdata['table'], figure_path, f'{cat[0]}_{cat[1]}',
                                             cat[0], cat[1], ['black', 'lightblue'], '' \
                                             f'Density of {cat[1]}')
        
            fig = px.histogram(sdata['table'].obs, x=cat[1], nbins=100, width=800, height=800)
            fig.update_layout(
                title=f"Total distribution {cat[1]} for cells of all samples"
            )
            helperfuncs.apply_general_plotly_layout(fig, True)
            figures.append(fig)
            fig.write_image(f"{figure_path}/histogram_{cat[1]}.png", scale=3)
            fig.write_image(f"{figure_path}/histogram_{cat[1]}.pdf", scale=3)

        with open(f'{figure_path}/convexity.html', 'w') as f:
            for fig in figures:
                f.write(fig.to_html(full_html=False, include_plotlyjs='cdn'))


def init_metric(enterprise):

    # These have to be defined.
    name = "convexity"
    submetrics = ["convexity_metric_cell", "convexity_min_nuceli"]
    modality = "hqcr"
    needs_metrics = []
    step_when_it_is_calculated = ["cellqc", "all"]
    loaded_for_analysis = True
    loaded_for_visualization = ["convexity_metric_cell", "convexity_min_nuceli"]

    # These are given my your metric calc function.
    args = [enterprise.cargo.sdata, f"{enterprise.args.output_dir}/cellqc/"]
    kwargs = None

    metric = core.metric.Metric(
        _calc_convexity, 
        name,
        submetrics,
        modality,
        needs_metrics = needs_metrics,
        step_when_it_is_calculated = step_when_it_is_calculated,
        loaded_for_analysis = loaded_for_analysis,
        loaded_for_visualization = loaded_for_visualization,
        args = args,
        kwargs = kwargs,
    )    
    
    return metric