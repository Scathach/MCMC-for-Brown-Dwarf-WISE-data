from __future__ import print_function

import emcee
import corner
import numpy as np
import scipy.optimize as op
import matplotlib.pyplot as pl
from matplotlib.ticker import MaxNLocator
from scipy.optimize import curve_fit
import PyAstronomy
from astropy.io import ascii

np.seterr(divide='ignore', invalid='ignore')

h = 6.626e-34 # J*s
c = 3.0e+8    # m/s
k = 1.38e-23  # m^2*kg*s^-2*K^-1

# using the planck function to caculate the intensity of spectral density
def planck(wav, T):
    a = 2.0*h*c**2
    b = h*c/(wav*k*T)
    intensity = a/ ( (wav**5) * (np.exp(b) - 1.0) )
    return intensity

def model(microns,Teff,logfactor):
    flux = ( (2.0*h*c**2)/(microns**5) )/( np.exp( (h*c)/(k*Teff*microns) ) - 1.0 )
    logflux = logfactor + np.log10(flux)
    return logflux

X = np.linspace(1,25,256,endpoint=True)

results_temperature = ascii.read("results_temperature.dat")
results_logfactor = ascii.read("results_logfactor.dat")

# Temperatures of other Brown Dwarfs used for comparison
MCMC_Temp = results_temperature[0][0]
MCMC_logfactor = results_logfactor[0][0]
T1, T1_name = 227, "WISE 1506+7027"
T2, T2_name = 450, "WISE 0410+1502"
T3, T3_name = 350, "WISE 1541−2250"

# temperature and Brown Dwarf decriptions
T1_description = T1_name + " (" + str(T1)+"K" + ")"
T2_description = T2_name + " (" + str(T2)+"K" + ")"
T3_description = T3_name + " (" + str(T3)+"K" + ")"
MCMC_description = "WISE 0855-0714" + " (" + str(MCMC_Temp)+"K" + ")"

# Ys used for plotting
Y1 = (np.log10(planck(X*10**-6,T1)))
Y2 = (np.log10(planck(X*10**-6,T2)))
Y3 = (np.log10(planck(X*10**-6,T3)))
Y4 = (model(X*10**-6, MCMC_Temp, MCMC_logfactor))
# Given data for WISE 0855-0714
data = ascii.read("SED.dat", data_start=6)
x = data[0][:]
y = data[1][:]
yerr = data[2][:]

# Plotting the error bars for WISE 0855-0714
pl.errorbar(x, y, yerr=yerr, fmt=".k")

# Plotting the log of planck function for each brown dwarf
plot1, = pl.plot(X,Y1, color="red", label=T1_description )
plot2, = pl.plot(X,Y2, color="green", label=T2_description )
plot3, = pl.plot(X,Y3, color="blue", label=T3_description )
plot4, = pl.plot(X,Y4, color="black", label=MCMC_description )
pl.legend([plot1,plot2,plot3,plot4],[T1_description, T2_description, T3_description, MCMC_description])
pl.xlabel("Wavelength (um)")
pl.ylabel("LOG10(Spectral Radiance)")

pl.show()
