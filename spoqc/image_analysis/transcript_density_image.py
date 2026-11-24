from spoqc.reporting import plots_enabled

import spatialdata as sd
import numpy as np
import dask.dataframe as dd
import os

from scipy.ndimage import convolve

from .. import helperfuncs

def generate_transcript_density_image(
        sdata,
        figure_path,
        spoqc_tmp_folder,
        imagedim,
        dim_x,
        dim_y,
        overwrite,
        chunk_size,
        *,
        kernel_radius=3,
        flip=False
):

    timer = helperfuncs.Timer()
    tmp_path = f"{spoqc_tmp_folder}/transcript_density_output_hqtr.parquet"
    if not os.path.exists(tmp_path) or ( os.path.exists(tmp_path) and overwrite ):

        print("[NOTE] Generate transcript density image")

        transcript_coords_df = sd.get_centroids(sdata['transcripts'], coordinate_system='global').compute()
        transcript_coords_df = transcript_coords_df.astype(int)
        xy_transcript_coords_df = transcript_coords_df.loc[:,['x','y']]

        print("[NOTE] Translate cooridnates")
        timer.start()
        counts = (
            xy_transcript_coords_df
            .value_counts(subset=['x','y'])      # returns a Series indexed by MultiIndex (x,y)
            .rename('count')
        )
        xy_transcript_density = helperfuncs.grouped_pixels_to_image(
            counts, imagedim, (dim_x, dim_y), dtype=counts.dtype,
        )
        timer.stop()


        # kernel_size = 2 * r + 1
        # Create circular kernel (disk mask)
        y, x = np.ogrid[-kernel_radius:kernel_radius+1, -kernel_radius:kernel_radius+1]
        mask = (x**2 + y**2) <= kernel_radius**2
        kernel = mask.astype(xy_transcript_density.dtype)

        print("[NOTE] Densitiy calculation")
        timer.start()
        xy_kernel_transcript_density = convolve(xy_transcript_density, kernel, mode='constant', cval=0)
        xy_kernel_transcript_density = np.flipud(xy_kernel_transcript_density)
        timer.stop()
        # xy_kernel_transcript_density = xy_kernel_transcript_density.astype(np.uint16) # conversion needed for cv2

        if plots_enabled() and figure_path is not None:
            nuclei_centroid_coords = sd.get_centroids(sdata['nucleus_boundaries'], coordinate_system='global').compute()

            if ( flip ):
                helperfuncs.plot_pixels(
                    figure_path,
                    xy_kernel_transcript_density,
                    imagedim,
                    'transcript_density',
                    'Transcript Density',
                    'gray',
                    True,
                    True,
                    points=nuclei_centroid_coords
                )
            else:
                helperfuncs.plot_pixels(
                    figure_path,
                    np.flipud(xy_kernel_transcript_density),
                    imagedim,
                    'transcript_density',
                    'Transcript Density',
                    'gray',
                    True,
                    True,
                    points=nuclei_centroid_coords
                )

        return xy_kernel_transcript_density.flatten()
    else:
        print("[NOTE] Load transcript density image")

        ddf = dd.read_parquet(
            tmp_path,
            columns=["transcript_density"],
            engine="pyarrow",
            calculate_divisions=True,
        )
        return ddf[f"transcript_density"].compute().to_numpy()
