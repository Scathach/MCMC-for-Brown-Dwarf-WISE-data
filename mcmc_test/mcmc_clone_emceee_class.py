import sys
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import ascii
import scipy.constants as con
import emcee
import corner
import scipy.optimize as op
import random
import os

# Get the data using the astropy ascii
data = ascii.read("SED.dat", data_start=6)

x = data[0][:]      # Wavelength column
y = data[1][:]     # log10(flux)
yerr = data[2][:]  # Error on log10(flux)

h = 6.626e-34
c = 3.0e+8
k = 1.38e-23

Teffmin = 10.0 #effective temperature minimum
Teffmax = 1000.0 #effective temperature maximum
logfacmin = -100.0 #log factor minimum
logfacmax = 0.0 #log factor maximum
#theatshape is 2 X 2 array
thetashape=np.array([[Teffmin,Teffmax],[logfacmin,logfacmax]])


class MCMCSetup(object):

    def __init__(self):
        pass

    def model(self,x, T,logfactor):

        #takes in the wavelength array approximate Temp and the log factor and returns and array of logflux
        wav = x * 1.0e-6
        flux = np.empty([len(wav)])
        logflux = np.empty([len(wav)])

        a = 2.0*h*c**2
        b = h*c/(wav*k*T)
        for i in range(len(wav)):
            a = 2.0*h*c**2
            b = h*c/(wav[i]*k*T)
            flux[i] = a/ ( (wav[i]**5) * (np.exp(b) - 1.0) )
            logflux[i] = logfactor + np.log10(flux[i])
        return logflux

    def log_like(self,x,logf,errlogf,theta):
        residuals = logf - self.model(x,theta[0],theta[1])
        loglike=0.0
        for i in range(len(x)):
            loglike = loglike - np.log(errlogf[i]) - 0.5*(residuals[i]/errlogf[i])**2
        loglike = loglike - 0.5*len(x)*np.log(2.0*np.pi)
        return loglike

    def log_prior(self,theta,thetashape):

        logpriors=np.empty([len(theta)])
        #logprior=0.0

        # Prior for theta[0]: Teff~logU[Teffmin,Teffmax]
        Teff = theta[0]
        Teffmin = thetashape[0][0]
        Teffmax = thetashape[0][1]
        if Teffmin < Teff < Teffmax:
            logpriors[0] = ( 1.0/(np.log(Teffmax) - np.log(Teffmin)) )/Teff
        else:
            logpriors[0] = -1.0e99 # -infinity

        # Prior for theta[1]: logfac~U[logfacmin,logfacmax]
        logfac = theta[1]
        logfacmin = thetashape[1][0]
        logfacmax = thetashape[1][1]
        if logfacmin < logfac < logfacmax:
            logpriors[1] = 1.0/(logfacmax - logfacmin)
        else:
            logpriors[1] = -1.0e99 # -infinity

        #logprior = np.sum(logpriors)

        return np.sum(logpriors)

    def lnprob(self,theta, x, y, yerr):
        lp = self.log_prior(theta,thetashape)

        if not np.isfinite(lp):
            return -np.inf

        return lp + self.log_like(x,y,yerr,theta) #loglikechain[0]

MCMC = MCMCSetup()

# Initialize the MCMC from a random point drawn from the prior
Teffinitial = np.exp( np.random.uniform(np.log(thetashape[0][0]),np.log(thetashape[0][1])) )
logfacinitial=np.random.uniform(thetashape[1][0],thetashape[1][1])
thetachain=np.array([[Teffinitial,logfacinitial]])

#Set the number of dimensions the MCMC algorithm will look for and the number of walkers
ndim, nwalkers = 2, 5
#Conversion Matrix required for the MHSampler to run
neg_lnprob = lambda *args: -MCMC.lnprob(*args)
#!!!!
res = op.minimize(neg_lnprob, x0=[200,-20], args=(x, y, yerr))
cov = res.hess_inv
#identify the initial position for MCMC algorithm
pos = [[Teffinitial,logfacinitial] + 1e-4*np.random.randn(ndim) for i in range(nwalkers)]
#Set up the sampler function
sampler = emcee.MHSampler(cov, dim = ndim, lnprobfn = MCMC.lnprob, args=(x, y, yerr))
# Clear and run the production chain.
number_of_samples = 12500

# Clear and run the production chain.
print("Running MCMC...")
sampler.run_mcmc(pos[0], 5000,rstate0=np.random.get_state())
print("Done.")

# Make the triangle plot.
burnin = 500
samples = sampler.chain[burnin:,:]#.reshape((-1, 2))

# Compute the quantiles.
samples[:] #= np.exp(samples[:])
T_mcmc, logfac_mcmc = list(map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]),
                             zip(*np.percentile(samples, [16, 50, 84],
                                                axis=0))))

print("""MCMC result:
    T = {0[0]} +{0[1]} -{0[2]}
    Log Factor = {1[0]} +{1[1]} -{1[2]}
""".format(T_mcmc, logfac_mcmc))


loglikeburn=np.median(samples[:,1])
j=-1
while True:
    j=j+1
    if samples[:,1][j] > loglikeburn:
        break
burnj=j
print( 'Burn point = ',burnj)

samples = sampler.chain[burnj:,:].reshape((-1, 2))

# Compute the quantiles.
samples[:] #= np.exp(samples[:])
T_mcmc, logfac_mcmc = list(map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]),
                             zip(*np.percentile(samples, [16, 50, 84],
                                                axis=0))))

print("""MCMC result with calculated burn point:
    T = {0[0]} +{0[1]} -{0[2]}
    Log Factor = {1[0]} +{1[1]} -{1[2]}
""".format(T_mcmc, logfac_mcmc))




################################################################################




dir_path = os.path.dirname(os.path.realpath(__file__)) + "\\emcee_model_graphs"
os.makedirs(dir_path, exist_ok=True)

# Ploting MCMC
plotting_wavelength = np.arange(x[0], 25.0, 0.01)

# Plot the initial guess results.
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off

data_1 = plt.errorbar(x, y, yerr=yerr, fmt=".r",color="#C80013")
line_1, = plt.plot(plotting_wavelength, MCMC.model(plotting_wavelength,samples[0][0],samples[0][1]), "--",color="#0A40AB", lw=1)
plt.ylabel('log10(fulx[erg s^-1 cm^-1 A^-1] )')
plt.xlabel("wavelength [um]")
plt.title('Initial Guess Result',color= "#302B2B", fontweight="bold")
plt.legend([data_1, line_1],['Available data','Curve with temperature from the initial guess'])
plt.savefig(dir_path+"\Initial Guess Result.png")
plt.close()

# Plot the MCMC results.
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off

data_2 = plt.errorbar(x, y, yerr=yerr,fmt='.',color="#C80013",ms="6")
line_2, = plt.plot(plotting_wavelength, MCMC.model(plotting_wavelength,T_mcmc[0],logfac_mcmc[0]), "--",color="#0A40AB", lw=1)
plt.ylabel('log10(fulx[erg s^-1 cm^-1 A^-1] )')
plt.xlabel("wavelength [um]")
plt.title('MCMC Result',color= "#302B2B", fontweight="bold")
plt.legend([data_2, line_2],['Available data','Curve with temperature from MCMC'])
plt.savefig(dir_path+"\MCMC results.png")
plt.close()

# Plot the path toward the MCMC results as vaules of logfactor and temperature without the burn point
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off

jlist=np.arange(len(samples))
plt.scatter(samples[:,0], samples[:,1], c=jlist, cmap='coolwarm')
plt.xlabel('Temperature [K]')
plt.ylabel('log10(factor)')
plt.title('Temperature vs log10(factor)',color= "#302B2B", fontweight="bold")
plt.colorbar().ax.set_title("Chain Number")
plt.savefig(dir_path+"\\1B Temperature vs logfactor.png")
plt.close()

np.max(samples[:,1])

#plotting log of likelyhood versus the chain number
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off

plt.plot(samples[:,1],color="#3513B6", lw=1)
plt.xlabel('Chain number')
plt.ylabel('loglike')
plt.title('Chain number vs loglike',color= "#302B2B", fontweight="bold")
plt.savefig(dir_path+"\\2B Chain number vs loglike.png")
#plt.show()
plt.close()

# Plot the path toward the MCMC results as vaules of logfactor and temperature with the burn point
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off

jlist=np.arange(len(samples))
plt.scatter(samples[burnj:,0], samples[burnj:,1], c=jlist[burnj:], cmap='coolwarm',alpha=0.5)
plt.xlabel('Temperature [K]')
plt.ylabel('log10(factor)')
plt.title('Temperature vs log10(factor)',color= "#302B2B", fontweight="bold")
plt.colorbar().ax.set_title("Chain Number")
plt.savefig(dir_path+"\\3B Temperature vs log10(factor).png")
#plt.show()
plt.close()

ascii.write(samples[burnj:,:], "chains.dat", overwrite= True)

# check mixing of temperature values
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off
plt.plot(samples[burnj:,0], color="#3513B6", lw=1)
plt.xlabel('Chain number')
plt.ylabel('Temperature [K]')
plt.title('Check mixing',color= "#302B2B", fontweight="bold")
plt.savefig(dir_path+"\\4B Check mixing, Temperature.png")
#plt.show()
plt.close()

# check mixing of log factor values
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off
plt.plot(samples[burnj:,1], color="#3513B6", lw=1)
plt.xlabel('Chain number')
plt.ylabel('log10(factor)')
plt.title('Check mixing',color= "#302B2B", fontweight="bold")
plt.savefig(dir_path+"\\5B Check mixing, log10(factor).png")
#plt.show()
plt.close()

# check mixing of log factor values using the mean
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off
temp=np.empty([len(samples)-burnj])
temp[0]=samples[burnj,0]
for i in range(burnj+1,len(samples)):
    temp[i-burnj]=np.mean(samples[burnj:i,0])
plt.plot(temp, color="#3513B6", lw=1)
plt.xlabel('Chain number')
plt.ylabel('Temperature [K]')
plt.title('Check mixing',color= "#302B2B", fontweight="bold")
plt.savefig(dir_path+"\\6B Check mixing, Temperature via mean.png")
#plt.show()
plt.close()

# check mixing of temperature values using the mean
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off
temp=np.empty([len(samples)-burnj])
temp[0]=samples[burnj,1]
for i in range(burnj+1,len(samples)):
    temp[i-burnj]=np.mean(samples[burnj:i,1])
plt.plot(temp, color="#3513B6", lw=1)
plt.xlabel('Chain number')
plt.ylabel('log10(factor)')
plt.title('Check mixing',color= "#302B2B", fontweight="bold")
plt.savefig(dir_path+"\\7B Check mixing, log10(factor) via mean.png")
#plt.show()
plt.close()

# check mixing for temperature and log factor usign mean
fig, ax = plt.subplots()

ax.spines['top'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(colors='#302B2B',top="off",bottom="off")
ax.yaxis.label.set_color('#302B2B')
ax.xaxis.label.set_color('#302B2B')
ax.grid(color='959595', linestyle='-', linewidth=.3)
plt.tick_params(
    axis='both',         # changes apply to the x-axis
    which='both',        # both major and minor ticks are affected
    left='off',          # ticks along the bottom edge are off
    right='off',         # ticks along the top edge are off
    bottom= 'off',       # ticks along the bottom edge are off
    top= 'off')          # tick along the top edhe are off

jlist=np.arange(len(samples))
plt.scatter(samples[burnj:,0], samples[burnj:,1], c=jlist[burnj:], cmap='coolwarm',alpha=0.5)
plt.xlabel('Temperature [K]')
plt.ylabel('log10(factor)')
plt.title('Check mixing',color= "#302B2B", fontweight="bold")
plt.colorbar().ax.set_title("Chain Number")
plt.savefig(dir_path+"\\8B Temperature vs log10(factor) with burn point.png")
plt.close()


fig = corner.corner(samples, labels=["$Temperature$", "$\ln\,f$"])
fig.savefig(dir_path+"\\Line-Triangle.png")

#Record the latest MCMC calculation into .dat file
T_mcmc_array = np.array(T_mcmc)
ascii.write(T_mcmc_array, "results.dat", names= ("Temperature", "+", "-"), overwrite= True)
