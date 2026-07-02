# ESPI_CODE
## Main functions in Main.py :

### capture_phase_series()           
is used for acquiring images
  - synchronization of camera and liquid crystal retarder
  - includes cropping tool in interface
### filter_and_subtract_all_sets()   
is used for image processing to acquire displacement maps
  - filtering and combining
  - unwrapping
  - displacement map calculations
### compute_strain_xx()              
is used for strain map calculation from displacement maps
