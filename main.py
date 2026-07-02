from plot_disp_lines_espi import *
from phase_series_acquisition import *
from full_image_processing import *
from plot_espi_strain import *
from plot_disp_lines_espi_and_sim import *
from crop_images_2 import *
from crop_images_3 import *
from disp_3D_plot import *
from crop_tiffs import *
from plot_single_displacement_tiff import *




#capture_phase_series()             # image acquisition

#crop_multiple_tiffs()

filter_and_subtract_all_sets(do_displacement=True)     # filter and combine, unwrap, displacement

#get_displacement(save_combined_png=True, save_multi_panel=True)
#plot_single_displacement_tiffs(colormap="jet", percentile=99.99, pixel_size_m=17e-6, save_png=True)

#compute_strain_xx(save_plot=True, save_tiff=False, pixel_size_um=17.0, fit_order=1, gauge_sizes=(5,), dotsize=2)

#plot_ux_tiff_sim(dist_from_center_mm=-9.5, sim_radius=12, center_adjust=True, include_sim=False, include_sum=True) #TO FIX gives 2x displacement
#plot_ux_combined_tiff(height_mm=0.5)    # height 0 at bottom, negative from top
#plot_ux_sum_tiff(height_mm=0.5)        # height 0 at bottom, negative from top


#crop_tiff_images_series()          # select 1 for series or multiples for just that selection
#crop_tiff_img_series_rect()

#plot_3D_from_tiff(Zangle=10, XYrot=-60)
