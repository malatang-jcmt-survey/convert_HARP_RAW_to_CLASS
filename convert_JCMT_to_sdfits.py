# Aim:
#     Convert the JCMT fits file generated by ndf2fits to the SDFITS format,
#     which is readable with GILDAS/CLASS.
#     The input fits file is the fits file converted from a JCMT sdf file,
#     containing all data (subscans and receptors) from one scan.
#
# Usage:
#   python
#
# Last update:
#   01-Nov.-2016 wrapped from IDL to python by Zhiyu Zhang, adding Tsys and time to each subscan.
#   03-Jan.-2017 add badTsys to determine the wrong system temperatures. Some receptors are dropped out automatically in starlink. We also need to remove these when converting to class.  
#   02-Jan.-2017 Now freq_step is automatically calculated from the SDF header which only contains the velocity step information.  


import os
import sys
from   scipy.constants     import *
from   astropy.io          import fits
from   numpy               import random
from   astropy.io          import ascii
import numpy             as np
import astropy.units     as u
import matplotlib.pyplot as plt


Tsys_hd = np.loadtxt("AllTsys.dat",delimiter=",")
badTsys = np.where(Tsys_hd.any() > 1e4 or Tsys_hd.any() < 0)
print("badTsys", badTsys)
print("badTsys", len(badTsys))

if len(badTsys) != 1:
    Tsys_hd[badTsys]   =  1e5


Exp_time_hd = np.loadtxt("All_on_time.dat",delimiter = ",")
filename    = str(sys.argv[1])

print(filename)

spec     = fits.open(filename)
spec.info()
header   = spec[0].header
data     = spec[0].data

#--------------------------------
a                    = data
where_are_NaNs       = np.isnan(a)
data[where_are_NaNs] = -999
#--------------------------------


print("It takes a while, please wait.")


subscans_num  = data.shape[0]
receptors_num = data.shape[1]
channels_num  = data.shape[2]


np.savetxt('numbers.dat', data.shape, delimiter=',')

receptor_location_file  = 'receptors_cat.FIT'
location                =  fits.open(receptor_location_file)[1].data


for i in range(0, subscans_num):
    for k in range(0, receptors_num):
        EXP_time               = Exp_time_hd[i]
        Tsys                   =  Tsys_hd[i*receptors_num + k]
        location_RA            = location[i*receptors_num + k][1]
        location_dec           = location[i*receptors_num + k][2]
        receptor_name          = location[i*receptors_num + k][3]
        spectrum               = np.full((1,1,1,channels_num),1.0)
        spectrum[0,0,0,:]      = data[i,k,:]
        spectrum               = spectrum.astype(np.float32)
        hdu                    = fits.PrimaryHDU(spectrum)
        hdulist                = fits.HDUList([hdu])
        header_out             = fits.Header()
        header_out['SIMPLE']   = header['SIMPLE']
        header_out['BITPIX']   = "32"
        header_out['NAXIS']    = 4
        header_out['NAXIS1  '] = header['NAXIS1  ']
        header_out['NAXIS2  '] = 1
        header_out['NAXIS3  '] = 1
        header_out['NAXIS4  '] = 1
        header_out['BLOCKED '] = True
#       header_out['BLANK   '] = np.int(2147483647)
        header_out['BSCALE  '] = 1.0
        header_out['BZERO   '] = 0.0
        header_out['DATAMIN '] = np.nanmax(spectrum)
        header_out['DATAMAX '] = np.nanmin(spectrum)
        header_out['BUNIT   '] = 'K'
        if header['CTYPE1'].strip() ==  "VRAD":
             header_out['CDELT1  '] = header['CDELT1  ']*1E3     # velocity resolution in m/s;  
             header_out['CRVAL1  '] = header['CRVAL1  ']*1E3     # velocity offset in m/s
             header_out['CTYPE1  '] = "VELO     " 
             header_out['RESTFREQ'] = header['RESTFRQ']# /(1+header['ZSOURCE'])
#            header_out['DELTAV']   = header['RESTFRQ']# /(1+header['ZSOURCE'])
        else:
            vel_to_freq            = u.doppler_relativistic(frequency * u.Hz)
            freq_step              = ((header['CDELT1  ']) *  u.km/u.s).to(u.Hz, equivalencies=vel_to_freq)-(0 *  u.km/u.s).to(u.Hz, equivalencies=vel_to_freq)
            header_out['CRVAL1  '] = header['CRVAL1  ']*1e3 # frequency in the reference channel;  header['CRVAL1  ']*1e3 # form km/s to m/s
            header_out['CDELT1  '] = freq_step.value        # freq resolution in Hz;  header['CDELT1  ']*1e3 # form km/s to m/s
            header_out['CTYPE1  '] = "FREQ     " 
            header_out['RESTFREQ'] = header['RESTFRQ']/(1+header['ZSOURCE'])

#       print("frequency:", frequency)
#       print("freq_step:", freq_step)
        header_out['CRPIX1  '] = header['CRPIX1  ']
        header_out['CTYPE2  '] = 'RA---GLS'
        header_out['EQUINOX']  = 0.200000000000E+004

        header_out['CRVAL2  '] = location_RA*180/pi
        header_out['CDELT2  '] = header['CDELT3  ']
        header_out['CRPIX2  '] = 0
#       header_out['BLANK   '] = -999 
        header_out['CTYPE3  '] = 'DEC--GLS'
        header_out['CRVAL3  '] = location_dec*180/pi
        header_out['CDELT3  '] = 1
        header_out['CRPIX3  '] = 0

        header_out['CTYPE4  '] = 'STOKES'
        header_out['CRVAL4  '] = 1.0
        header_out['CDELT4  '] = 0.0
        header_out['CRPIX4  '] = 0.0

        header_out['TELESCOP'] = header['TELESCOP']+receptor_name
        header_out['scan-num'] = header['OBSNUM']
        header_out['OBJECT']   = header['OBJECT']

        header_out['LINE    '] = header['MOLECULE']+header['TRANSITI'].replace(" ", "")
        header_out['VELO-LSR'] = 0                    # in mm/s change it to zero, to fit with gildas
        header_out['IMAGFREQ'] = header['IMAGFREQ']   # Hz
        header_out['TSYS    '] = Tsys
        header_out['DATE-OBS'] = header['DATE']
        header_out['DATE-RED'] = header['DATE']
        header_out['TIMESYS']  = 'UTC'

        header_out['OBSTIME '] = EXP_time # s
        header_out['TAU-ATM '] = header['TAU225ST']
        header_out['BEAMEFF '] = header['ETAL']
        header_out['FORWEFF '] = 1
        header_out['ELEVATIO'] = header['ELSTART']
        header_out['AZIMUTH']  = header['AZSTART']
        if (np.nanmean(data[i,k,:]) > -900):
            fits.writeto('test_scan'+str(i)+'_rec'+str(k)+'.fits', spectrum, header_out, clobber=True)
        else:
            print('NaN array dropped')




cmd  = r"rm AllTsys*"
os.system(cmd)

cmd  = r"rm All_on_time*"
os.system(cmd)


