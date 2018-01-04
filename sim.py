## Import Package Dependences ##
import sys
from numpy import *
from openopt import *
import matplotlib.pyplot as plt
import csv
import collections
import pandas as pd
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
from scipy.interpolate import spline
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.mlab as mlab
random.seed(1)


#==============================
## Generate input csv file with column headings
# > python sim.py -setup

setup_head = ('index', 'kt (s-1)', 'kt error', 'k_t (s-1)', 'k_t error', 'ki (s-1)', 'ki error', 'k_i (s-1)', 'k_i error', 'kta (s-1)', 'kta error', 'kat (s-1)', 'kat error')

if str(sys.argv[1]) == "-setup":
	with open('batch_input.csv', 'wb') as s:
		writer = csv.writer(s)
		writer.writerow(setup_head)
		exit()


## PDF Plot Outputs ##
pp = PdfPages('kobs_plots.pdf')
pf = PdfPages('kpol_plots.pdf')
pg = PdfPages('Fpol_Histogram.pdf')
ph = PdfPages('kpol_Histogram.pdf')
pi = PdfPages('Kd_Histogram.pdf')

## Lists for writing out batch output results ##
fobs_out = []
fobs_out_err = []
kpol_out = []
kpol_out_err =[]
kd_out = []
kd_out_err = []
kobs_out = []
kobs_out_err = []

# Number of MonteCarlo iterations
MC_num = int(sys.argv[2])

# Scheme 1: Correct incorporation of dCTP-dG base pair
# Scheme 2: Incorrect incorporation of dTTP-dG base pair

#Simulation time points and dNTP concentrations
TimePtsCorrect = [.001, .005, .01, .05, .1, .2, .3, .5, 1]
TimePtsMismatch = [1, 2, 3, 4, 5, 6, 7, 10, 15, 30, 60]

NTPConcCorrect = [0.625, 1.25, 2.5, 5, 10, 20, 40, 80, 200]
NTPConcMismatch = [50, 100, 200, 300, 500, 750, 1000, 1500]

##=====================##
# Fitting Equations
##====================##
def expfun(p, X):
	a,R = p
	return a*(1-exp(-R*X))
#==
def expfit(X, Y, p0):
	#-
	def chi2(p):
		YS = expfun(p,X)
		return sum((Y-YS)**2)
	#-
	nlp = NLP(chi2, p0)
	result = nlp.solve('ralg', iprint= -1)
	return result.xf
#==
def polfun(p, X):
	k,r = p
	return ((r*X)/(k+X))
#==
def polfit (X,Y, p0):
	#-
	def chi2(p):
		YS = polfun(p, X)
		return sum((Y-YS)**2)
	#-
	nlp = NLP(chi2, p0)
	result = nlp.solve('ralg', iprint = -1)
	return result.xf
#=======================
#=====================
def Fitting(SchemeDict, TimeList, NTPlist, ProdAmblitudeFitGuess, kObsGuess, kPolGuess, KdGuess):
#Fitting for kobs and kpol. Inputs are the approprate Scheme Dict of [dNTP] and Time point resutls, as well as
#the approprate Correct/Incorrect Time and [dNTP] conditions 
	x = 0
	ListOfkObs = []
	for key in SchemeDict.keys():
	# Fetch n or n+x list from Dict of 'product populations'
		temp_list = list(SchemeDict.values()[x])
	# Flatten list of list to single list
		ProdValues = [val for sublist in temp_list for val in sublist]
	
	# Add one to access next key in next cycle
		x = x+1 
		# Data formatting
		data1 = column_stack(TimeList)
		data2 = column_stack(ProdValues)
		# Fitting for kobs
		a,R = expfit(data1, data2, [ProdAmblitudeFitGuess, kObsGuess])
		ListOfkObs.append(R)
		plt.plot(data1, data2, 'ko')
		if TimeList == TimePtsCorrect:
			test_time = linspace(0,1,1000)
			test_result1 = [(a*(1-exp(value*-R))) for value in test_time]
			plt.plot(test_time, test_result1, color = 'C0')
		else:
			test_time = linspace(0,60,1000)
			test_result1 = [(a*(1-exp(value*-R))) for value in test_time]
			plt.plot(test_time, test_result1, color = 'C0')
		
	# Final plot for all [dNTP]. 
	plt.ylabel('Product', fontsize = 14)
	plt.xlabel('time (s)', fontsize = 14)
	plt.tight_layout()
	plt.savefig(pp, format = 'pdf')
	plt.clf()
	
	## Fitting for kpol from kobs values ##
	# Data Formatting
	data1 = column_stack(NTPlist)
	data2 = column_stack(ListOfkObs)
	# Fitting
	k,r = polfit(data1, data2, [kPolGuess, KdGuess])
	# Plotting	
	plt.plot(data1, data2, 'ko')
	if TimeList == TimePtsCorrect:
		test_ntp = linspace(0,200,1000)
		test_result = [(r*x)/(k+x) for x in test_ntp]
	else:
		test_ntp = linspace(0,1500,1000)
		test_result = [(r*x)/(k+x) for x in test_ntp]
	plt.plot(test_ntp, test_result)
	plt.xlabel('dNTP Conc. (uM)', fontsize=14)
	plt.ylabel('kobs (s-$^1)$', fontsize = 14)
	plt.tight_layout()
	plt.savefig(pf, format = 'pdf')
	plt.clf()
	return r, k

#===================
# Kinetic Simulations
# Correct and Incorrect Simulations share the same set of rate constants, save for the 
# inclusion of tautomerization/ionization for incorrect incorporations.

# Shared rate constants are declared here; dNTP on and off rate are declared in each scheme
if sys.argv[3] == 'E':
	k_1c = 1900
	k_1i = 70000
	k2 = 268 #forward conformational change rate constant
	k_2 = 100 #reverse conformational change rate constant
	k3 = 9000 #forward chemisty rate constant
	k_3 = .004 #reverse chemisty rate constant
	fitc_guess = 268
elif sys.argv[3] == 'B':
	k_1c = 1000
	k_1i = 65000
	k2 = 1365
	k_2 = 11.9
	k3 = 6.4
	k_3 = .001
	fitc_guess = 6
elif sys.argv[3] == 'T7':
	k_1c = 1000
	k_1i = 70000
	k2 = 660
	k_2 = 1.6
	k3 = 360
	k_3 = .001
	fitc_guess = 200
else:
	print 'Define Polymerase Model'
	exit()

k_2t = k_2
k2t = k2 
k2i = k2

#===================
#Run Kinetic Sheme #1 
def SimulateSchemeOne():
	SchemeOneProduct = []
	for Conc in NTPConcCorrect:
		# Defining additioanl rate constants and starting populations
		C0 = array([1.0, 0.0, 0.0, 0.0]) #Simulation starts with 100% population as E-DNA. 
		k1 = Conc * 100  # dNTP on rate

		# Rate Matrix
		K = zeros((4,4))
		K[0, 0] = -k1
		K[0, 1] = k_1c
		K[1, 0] = k1
		K[1, 1] = -k_1c-k2
		K[1, 2] = k_2
		K[2, 1] = k2
		K[2, 2] = -k_2-k3
		K[2, 3] = k_3
		K[3, 2] = k3
		K[3, 3] = -k_3
		
		w,M = linalg.eig(K)
		M_1 = linalg.inv(M)

		# Simulate for each timepoint
		for num in TimePtsCorrect:
			T = linspace (0, float(num), 2)
			B = zeros(T.shape)
			C = zeros(T.shape)
			D = zeros(T.shape)
			E = zeros(T.shape)
			

			for i,t in enumerate(T):
				A = dot(dot(M,diag(exp(w*t))), M_1)
				B[i] = dot(A[0,:], C0)
				C[i] = dot(A[1,:], C0)
				D[i] = dot(A[2,:], C0)
				E[i] = dot(A[3,:], C0)
				
				
			SchemeOneProduct.append(E[-1])
# Data Handling
	SchemeOneDct  = collections.OrderedDict()
	x = 0
	for Number in NTPConcCorrect:
		SchemeOneDct['%s' % Number] = [SchemeOneProduct[x:x+len(TimePtsCorrect)]] 
		x = x + len(TimePtsCorrect)
	
	kpolOne, kdOne = Fitting(SchemeOneDct, TimePtsCorrect, NTPConcCorrect, .99, 5, fitc_guess, k_1c / 100)
	return kpolOne, kdOne
	
def SimulateSchemeTwo(kt, k_t, ki, k_i, kti, kit, k_2i):
	SchemeTwoProduct = []
	for Conc in NTPConcMismatch:
		C0 = array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
		k1 = Conc * 100 # dNTP on rate	

		K = zeros((6, 6))
		K[0, 0] = -k1
		K[0, 1] = k_1i
		K[1, 0] = k1
		K[1, 1] = -k_1i-kt-ki
		K[1, 2] = k_t
		K[1, 3] = k_i
		K[2, 1] = kt
		K[2, 2] = -k_t-k2t-kti
		K[2, 3] = kit
		K[2, 4] = k_2t
		K[3, 1] = ki
		K[3, 2] = kti
		K[3, 3] = -k_i-k2i-kit
		K[3, 4] = k_2i
		K[4, 2] = k2t
		K[4, 3] = k2i
		K[4, 4] = -k_2t-k_2i-k3
		K[4, 5] = k_3
		K[5, 4] = k3
		K[5, 5] = -k_3

		w,M = linalg.eig(K)
		M_1 = linalg.inv(M)

		for num in TimePtsMismatch:
			T = linspace (0, float(num), 2)
			B = zeros(T.shape)
			C = zeros(T.shape)
			D = zeros(T.shape)
			E = zeros(T.shape)
			F = zeros(T.shape)
			G = zeros(T.shape)
			

			for i,t in enumerate(T):
				A = dot(dot(M,diag(exp(w*t))), M_1)
				B[i] = dot(A[0,:], C0)
				C[i] = dot(A[1,:], C0)
				D[i] = dot(A[2,:], C0)
				E[i] = dot(A[3,:], C0)
				F[i] = dot(A[4,:], C0)
				G[i] = dot(A[5,:], C0)
				
				
			SchemeTwoProduct.append(G[-1])

	SchemeTwoDct = collections.OrderedDict()
	
	x = 0
	for Number in NTPConcMismatch:
		SchemeTwoDct['%s' % Number] = [SchemeTwoProduct[x:x+len(TimePtsMismatch)]]
		x = x + len(TimePtsMismatch)

	kpolTwo, kdTwo = Fitting(SchemeTwoDct, TimePtsMismatch, NTPConcMismatch, .9, .5, .5, k_1i / 100)
	return kpolTwo, kdTwo

def simulation_routine(params):

    # Unpack params/errors
    kt, k_t, ki, k_i, kat, kta, k_2i = params

    # Run the Simulation
    kpol, kd = SimulateSchemeTwo(kt, k_t, ki, k_i, kat, kta, k_2i)
    fobs = (kpol / kd) / (kpol_correct / kd_correct)
    kobs = (kpol * 100) / (kd + 100)
    kpol_list.append(kpol)
    kd_list.append(kd)
    kobs_list.append(kobs)
    print "kpol:", format(kpol, '.3f'), "kobs[100 uM]:", format(kobs, '.3f'), "Kd:", format(kd, '.0f'), "Fpol:", fobs
    return fobs

######################################
# Propagating error by drawing
# parameters from normal distribution
# given by associated parameter error
######################################
kpol_correct, kd_correct = SimulateSchemeOne()
print kpol_correct, kd_correct

RateConstants = pd.read_csv(str(sys.argv[1]))
RateConstants.columns = ['index', 'kt', 'kt_err', 'k_t', 'k_t_err', 'ki', 'ki_err', 'k_i', 'k_i_err', 'kta', 'kta_err', 'kat', 'kat_err']

sim_num = len(list(enumerate(RateConstants.index, 1)))
sim_count = 1
for value in RateConstants.index:
	print "Simulation: %s / %s" % (sim_count, sim_num)
	kt, kt_err = RateConstants.kt[value], RateConstants.kt_err[value]
	k_t, k_t_err = RateConstants.k_t[value], RateConstants.k_t_err[value]
	ki, ki_err = RateConstants.ki[value], RateConstants.ki_err[value]
	k_i, k_i_err = RateConstants.k_i[value], RateConstants.k_i_err[value]
	kat, kat_err = RateConstants.kat[value], RateConstants.kat_err[value]
	kta, kta_err = RateConstants.kta[value], RateConstants.kta_err[value]
	if ki == 0:
		k_2i = 0
	else:
		k_2i = 100

# Loop over number of MC iterations
	fobs_list = []
	kpol_list = []
	kd_list = []
	kobs_list = []

	for iteration in range(MC_num):
		new_kt = random.normal(loc=kt, scale=kt_err)
		new_k_t = random.normal(loc=k_t, scale=k_t_err)
		new_ki = random.normal(loc=ki, scale=ki_err)
		new_k_i = random.normal(loc=k_i, scale=k_i_err)
		new_kat = random.normal(loc=kat, scale=kat_err)
		new_kta = random.normal(loc=kta, scale=kta_err)

    	# Now feed these randomly drawn permutations of the parameters
    	# to your target function (i.e. your kinetic sim) and get the
    	# distribution of fobs (or whatever) values. From this you
    	# can calculate the SD/SEM/etc of fobs using the error in 
    	# all the dependent parameters
		fobs_list.append(simulation_routine(params=[new_kt, new_k_t, new_ki, new_k_i, new_kat, new_kta, k_2i]))
		print "MC Error Iteration: %s / %s" % (iteration+1, MC_num)
	sim_count += 1
			
	fobs = asarray(fobs_list)
	del fobs_list[:]
	mu_fobs, sigma_fobs = fobs.mean(), fobs.std()
	print("Mean of Fobs:", mu_fobs)
	print("Std.dev of Fobs:", sigma_fobs)
	fobs_out.append(mu_fobs)
	fobs_out_err.append(sigma_fobs)

	kpol = asarray(kpol_list)
	del kpol_list[:]
	mu_kpol, sigma_kpol = kpol.mean(), kpol.std()
	print("Mean of kpol:", mu_kpol)
	print("Std.dev of kpol:", sigma_kpol)
	kpol_out.append(mu_kpol)
	kpol_out_err.append(sigma_kpol)

	kd = asarray(kd_list)
	del kd_list[:]
	mu_kd, sigma_kd = kd.mean(), kd.std()
	print("Mean of Kd:", mu_kd)
	print("Std.dev of Kd:", sigma_kd)
	kd_out.append(mu_kd)
	kd_out_err.append(sigma_kd)

	kobs = asarray(kobs_list)
	del kobs_list[:]
	mu_kobs, sigma_kobs = kobs.mean(), kobs.std()
	print("Mean of kobs:", mu_kobs)
	print("Std.dev of kobs:", sigma_kobs)
	kobs_out.append(mu_kobs)
	kobs_out_err.append(sigma_kobs)

	# Plot distribution of calculated fobs
	# - used this code: https://stackoverflow.com/questions/7805552/fitting-a-histogram-with-python
	fig, ax = plt.subplots(dpi=120)
	n, bins, patches = plt.hist(fobs, 60, normed=1, facecolor='skyblue', alpha=0.75)
	y = mlab.normpdf(bins, mu_fobs, sigma_fobs)
	l = ax.plot(bins, y, 'r-', linewidth=2)

	# Set labels
	ax.set_xlabel(r'$F_{obs}$', fontsize=16)
	ax.set_ylabel("Normalized Counts", fontsize=16)
	ax.set_title(r"$F_{obs}\,|\,\mu=%0.6f\,|\,\sigma=%0.6f$" % (mu_fobs, sigma_fobs), fontsize=14)
	plt.tight_layout()
	plt.savefig(pg, format = 'pdf')
	plt.clf()

	# Plot distribution of calculated kpol
	fig, ax = plt.subplots(dpi=120)
	n, bins, patches = plt.hist(kpol, 60, normed=1, facecolor='skyblue', alpha=0.75)
	y = mlab.normpdf(bins, mu_kpol, sigma_kpol)
	l = ax.plot(bins, y, 'r-', linewidth=2)

	# Set labels
	ax.set_xlabel(r'$k_{pol}$', fontsize=16)
	ax.set_ylabel("Normalized Counts", fontsize=16)
	ax.set_title(r"$K_{pol}\,|\,\mu=%0.6f\,|\,\sigma=%0.6f$" % (mu_kpol, sigma_kpol), fontsize=14)
	plt.tight_layout()
	plt.savefig(ph, format = 'pdf')
	plt.clf()

	# Plot distribution of calculated kd
	fig, ax = plt.subplots(dpi=120)
	n, bins, patches = plt.hist(kd, 60, normed=1, facecolor='skyblue', alpha=0.75)
	y = mlab.normpdf(bins, mu_kd, sigma_kd)
	l = ax.plot(bins, y, 'r-', linewidth=2)

	# Set labels
	ax.set_xlabel(r'$K_{d}$', fontsize=16)
	ax.set_ylabel("Normalized Counts", fontsize=16)
	ax.set_title(r"$K_{d}\,|\,\mu=%0.6f\,|\,\sigma=%0.6f$" % (mu_kd, sigma_kd), fontsize=14)
	plt.tight_layout()
	plt.savefig(pi, format = 'pdf')
	plt.clf()

	# Plot distribution of calculated kobs
	fig, ax = plt.subplots(dpi=120)
	n, bins, patches = plt.hist(kobs, 60, normed=1, facecolor='skyblue', alpha=0.75)
	y = mlab.normpdf(bins, mu_kobs, sigma_kobs)
	l = ax.plot(bins, y, 'r-', linewidth=2)

	# Set labels
	ax.set_xlabel(r'$k_{obs}$', fontsize=16)
	ax.set_ylabel("Normalized Counts", fontsize=16)
	ax.set_title(r"$k_{obs}\,|\,\mu=%0.6f\,|\,\sigma=%0.6f$" % (mu_kobs, sigma_kobs), fontsize=14)
	plt.tight_layout()
	plt.savefig(pi, format = 'pdf')
	plt.clf()

## Write Out Final Results ##
Master = zip(fobs_out, fobs_out_err, kpol_out, kpol_out_err, kd_out, kd_out_err, kobs_out, kobs_out_err)
heading = ('Fobs (mean)', 'Fobs (Std. Dev.)', 'kpol (mean)', 'kpol (Std.Dev)', 'Kd (mean)', 'Kd (Std. Dev', 'kobs @ 100uM dNTP', 'kobs_err')
error_info = ('Number of MC iteration', '%s' % MC_num)
with open('output.csv', 'wb') as f:
	writer = csv.writer(f)
	writer.writerow(error_info)
	writer.writerow(heading)
	writer.writerows(Master)
#=========================

pp.close()
pf.close()
pg.close()
ph.close()
pi.close()
