from plot_disp_lines_espi import *
from a_phase_series_acquisition import *
from c_img_processing_main import *
from e_plot_espi_strain import *
from plot_disp_lines_espi_and_sim import *
from a__crop_images_2 import *
from Other_code_files.crop_images_3 import *
from plot_disp_3D_plot import *
from Other_code_files.crop_tiffs import *
from plot_single_displacement_tiff import *
from b_nancrop_expand_crack_espi import *

pixel_size_m = 8.4e-6

if __name__ == "__main__":

    #capture_phase_series()             # image acquisition

    #crackcrop_all_espi_sets(grow_threshold=30, similarity_threshold=20, min_component_size=100)

    filter_and_subtract_all_sets(do_displacement=True, filter3_version='A', include_diagnostics=False, pixel_size_m=pixel_size_m)     # filter and combine, unwrap, displacement

    #get_displacement(save_combined_png=True, save_multi_panel=True)
    #plot_single_displacement_tiffs(colormap="jet", percentile=99.99, pixel_size_m=pixel_size_m, save_png=True)

    #compute_strain_xx(save_plot=True, save_tiff=False, pixel_size_um=pixel_size_m*10**6, fit_order=1, gauge_sizes=(5,), dotsize=2)

    #plot_ux_tiff_sim(dist_from_center_mm=-7, sim_radius=12, center_adjust=True, include_sim=False, include_sum=True) #TO FIX gives 2x displacement
    #plot_ux_combined_tiff(height_mm=0.5)    # height 0 at bottom, negative from top
    #plot_ux_sum_tiff(height_mm=0.5, pixel_size_m=pixel_size_m)        # height 0 at bottom, negative from top

    #crop_multiple_tiffs()
    #crop_tiff_images_series()          # select 1 for series or multiples for just that selection
    #crop_tiff_img_series_rect()

    #plot_3D_from_tiff(Zangle=10, XYrot=-60)
