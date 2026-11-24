
# In[]
import dask.dataframe as dd
import pandas as pd

from .. import helperfuncs
from .. import hqr

# In[]
def start_pixel_mask_refinement(
        figure_path,
        spoqc_tmp_folder,
        modality,
        dim_x,
        dim_y,
        chunk_size,
        *,
        beta=1.5,
        max_iter=15,
        staining=None
    ):

    suffix = modality
    prefix = 'raw'
    if ( staining ):
        figure_path = f'{figure_path}/{modality}/{modality}_refinement/{staining}/'
        suffix = f'{modality}_{staining}'
    else:
        figure_path = f'{figure_path}/{modality}/{modality}_refinement/'

    image_ddf = dd.read_parquet(
        f'{spoqc_tmp_folder}/mask_{prefix}_output_{suffix}',
        columns=[f"{suffix}_beliefs"],
        engine="pyarrow",
        index=False,
    )
    
    beliefs_raw = image_ddf[f"{suffix}_beliefs"].to_dask_array().compute()

    # Start the refinement of the proability for the pixel score.
    beliefs, labels = hqr.markov_random_field_zarr_parallel.first_version_loopy_belief_propagation_parallel(
        beliefs_raw.reshape((dim_x, dim_y)),
        spoqc_tmp_folder,
        modality,
        beta=beta,
        max_iter=max_iter,
        normalize='total'
    )

    labels = labels[:]
    hqr.markov_random_field_zarr_parallel.visualize_markov_calculation(
        beliefs_raw.reshape((dim_x, dim_y)),
        labels,
        figure_path
    )

    #  Write out masks.
    print(f"[NOTE] Write out {suffix} masks")

    columns = {
        f"{suffix}_beliefs": beliefs_raw,
        f"{suffix}_beliefs_smoothed": beliefs.ravel(),
        f"{suffix}_mask_smoothed": labels.ravel(),
    }
    n_rows = len(beliefs_raw)
    n_partitions = max(1, -(-n_rows // chunk_size))
    rows_per_partition = -(-n_rows // n_partitions)
    offsets = (*range(0, n_rows, rows_per_partition), n_rows)

    def partition(bounds):
        start, stop = bounds
        return pd.DataFrame(
            {name: values[start:stop] for name, values in columns.items()},
            index=pd.RangeIndex(start, stop),
            copy=False,
        )

    # Build only the partition being written, with a global row index so the
    # physical pixel order survives the Parquet round trip.
    image_ddf = dd.from_map(
        partition, list(zip(offsets, offsets[1:])),
        meta=partition((0, 0)), divisions=(*offsets[:-1], n_rows - 1),
    )

    helperfuncs.ddf_to_parquet(
        image_ddf, f'mask_smoothed_{prefix}', spoqc_tmp_folder, [], suffix,
        include_index=False,
    )

