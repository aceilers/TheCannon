"""This runs Step 1 of The Cannon: 
    uses the training set to solve for the best-fit model."""

# Currently, this is a bit sketchy...there were sections of the original code that I didn't understand. have e-mailed MKN, will update. 

from dataset import Dataset
import numpy as np
import math
import pylab
import matplotlib.pyplot as plt
from matplotlib import rc
import os

def do_one_regression_at_fixed_scatter(lams, fluxes, ivars, x, scatter):
    """
    Params
    ------
    lams: ndarray, [npixels]
    spectra: ndarray, [nstars, 3]
    x=coefficients of the model: ndarray, [nstars, nlabels]
    scatter: ndarray, [nstars]

    Returns
    ------
    coeff: ndarray
        coefficients of the fit
    xTCinvx: ndarray
        inverse covariance matrix for fit coefficients
    chi: float
        chi-squared at best fit
    logdet_Cinv: float
        inverse of the log determinant of the cov matrix
    """
    err2 = 100**2*np.ones(len(ivars))
    mask = ivars != 0
    err2[mask] = 1. / ivars[mask]
    Cinv = 1. / (err2 + scatter**2)
    xTCinvx = np.dot(x.T, Cinv[:, None] * x) 
    xTCinvf = np.dot(x.T, Cinv * fluxes)
    try:
        coeff = np.linalg.solve(xTCinvx, xTCinvf) # this is the model!
    except np.linalg.linalg.LinAlgError:
        print "np.linalg.linalg.LinAlgError, do_one_regression_at_fixed_scatter"
        print xTCinvx, xTCinvf, lams, fluxes
    assert np.all(np.isfinite(coeff))
    chi = np.sqrt(Cinv) * (fluxes - np.dot(x, coeff))
    logdet_Cinv = np.sum(np.log(Cinv))
    return (coeff, xTCinvx, chi, logdet_Cinv)

def do_one_regression(lams, fluxes, ivars, x):
    """
    Optimizes to find the scatter associated with the best-fit model.

    This scatter is the deviation between the observed spectrum and the model.
    It is wavelength-independent, so we perform this at a single wavelength.

    Input
    -----
    lams: ndarray, [npixels]
    spectra: ndarray, [nstars, 2] 
    x = coefficients of the model: ndarray, [nstars, nlabels]

    Output
    -----
    output of do_one_regression_at_fixed_scatter
    """
    # cover the full order of the scatter term, scatter << max term
    ln_scatter_vals = np.arange(np.log(0.0001), 0., 0.5) 
    # will minimize over the range of scatter possibilities
    chis_eval = np.zeros_like(ln_scatter_vals)
    for jj, ln_scatter_val in enumerate(ln_scatter_vals):
        coeff, xTCinvx, chi, logdet_Cinv = do_one_regression_at_fixed_scatter(
                lams, fluxes, ivars, x, scatter = np.exp(ln_scatter_val))
        chis_eval[jj] = np.sum(chi * chi) - logdet_Cinv
    # What do the below two cases *mean*?
    if np.any(np.isnan(chis_eval)):
        best_scatter = np.exp(ln_scatter_vals[-1]) 
        return do_one_regression_at_fixed_scatter(
                lams, fluxes, ivars, x, scatter = best_scatter) + (best_scatter, )
    lowest = np.argmin(chis_eval) # the best-fit scatter value?
    # If it was unsuccessful at finding it...
    if lowest == 0 or lowest == len(ln_scatter_vals) + 1: 
        best_scatter = np.exp(ln_scatter_vals[lowest])
        return do_one_regression_at_fixed_scatter(lams, fluxes, ivars, x, 
                scatter = best_scatter) + (best_scatter, )
    ln_scatter_vals_short = ln_scatter_vals[np.array(
        [lowest-1, lowest, lowest+1])]
    chis_eval_short = chis_eval[np.array([lowest-1, lowest, lowest+1])]
    z = np.polyfit(ln_scatter_vals_short, chis_eval_short, 2)
    f = np.poly1d(z)
    fit_pder = np.polyder(z)
    fit_pder2 = pylab.polyder(fit_pder)
    best_scatter = np.exp(np.roots(fit_pder)[0])
    return do_one_regression_at_fixed_scatter(
            lams, fluxes, ivars, x, scatter = best_scatter) + (best_scatter, )

def train_model(reference_set):
    """
    This determines the coefficients of the model using the training data

    Input: the reference_set, a Dataset object (see dataset.py)
    Returns: the model, which consists of...
    -------
    coefficients: ndarray, (npixels, nstars, 15)
    the covariance matrix
    scatter values
    red chi squareds
    the pivot values
    the label vector
    """
    print "Training model..."
    label_names = reference_set.label_names
    label_vals = reference_set.label_vals 
    nlabels = len(label_names)
    lams = reference_set.lams
    fluxes = reference_set.fluxes
    ivars = reference_set.ivars
    nstars = fluxes.shape[0]
    npixels = len(lams)

    # Establish label vector
    pivots = np.mean(label_vals, axis=0)
    ones = np.ones((nstars, 1))
    linear_offsets = label_vals - pivots
    quadratic_offsets = np.array([np.outer(m, m)[np.triu_indices(nlabels)] 
        for m in (label_vals - pivots)])
    x = np.hstack((ones, linear_offsets, quadratic_offsets))
    x_full = np.array([x,]*npixels) 

    # Perform REGRESSIONS
    fluxes = fluxes.swapaxes(0,1) # for consistency with x_full
    ivars = ivars.swapaxes(0,1)
    blob = map(do_one_regression, lams, fluxes, ivars, x_full) #one per pix
    coeffs = np.array([b[0] for b in blob])
    covs = np.array([np.linalg.inv(b[1]) for b in blob])
    chis = np.array([b[2] for b in blob])
    chisqs = np.array([np.dot(b[2],b[2]) - b[3] for b in blob])
    # is the above actually supposed to be b[2]*b[2]? 
    scatters = np.array([b[4] for b in blob]) # how could there be a b[4]?
                        # there are only four outputs from do_one_regression_at_
                        # fixed_scatter...confused
    
    # Calc red chi sq
    all_chisqs = chis*chis
    chisqs = np.sum(all_chisqs, axis=0) # now we have one per star
    dof = npixels-nlabels
    red_chisqs = chisqs/dof
    model = coeffs, covs, scatters, red_chisqs, pivots, x_full
    print "Done training model"
    return model

def model_diagnostics(reference_set, model):
    """Run a set of diagnostics on the model.

    Plot the 0th order coefficients as the baseline spectrum. 
    Overplot the continuum pixels.
    
    Plot each label's leading coefficient as a function of wavelength.
    Color-code by label.

    Histogram of the chi squareds of the fits.
    Dotted line corresponding to DOF = npixels - nlabels
    """
    lams = reference_set.lams
    label_names = reference_set.label_names
    coeffs_all, covs, scatters, red_chisqs, pivots, label_vector = model
   
    # Baseline spectrum with continuum
    baseline_spec = coeffs_all[:,0]
    fig, axarr = plt.subplots(2, sharex=True)
    plt.xlabel(r"Wavelength $\lambda (\AA)$")
    plt.xlim(min(lams), max(lams))
    ax = axarr[0]
    ax.plot(lams, baseline_spec,
            label=r'$\theta_0$' + "= the leading fit coefficient")
    contpix_lambda = list(np.loadtxt("pixtest4_lambda.txt", 
        usecols = (0,), unpack =1))
    y = [1]*len(contpix_lambda)
    ax.scatter(contpix_lambda, y, s=1,
            label="continuum pixels")
    ax.legend(loc='lower right', prop={'family':'serif', 'size':'small'})
    ax.set_title("Baseline Spectrum with Continuum Pixels")
    ax.set_ylabel(r'$\theta_0$')
    ax = axarr[1]
    ax.plot(lams, baseline_spec, 
            label=r'$\theta_0$' + "= the leading fit coefficient")
    contpix_lambda = list(np.loadtxt("pixtest4_lambda.txt", 
        usecols = (0,), unpack =1))
    ax.scatter(contpix_lambda, y, s=1,
            label="continuum pixels")
    ax.set_title("Baseline Spectrum with Continuum Pixels, Zoomed")
    ax.legend(loc='upper right', prop={'family':'serif', 'size':'small'})
    ax.set_ylabel(r'$\theta_0$')
    ax.set_ylim(0.95, 1.05)

    filename = "baseline_spec_with_cont_pix.png"
    print "Diagnostic plot: fitted 0th order spectrum, cont pix overlaid." 
    print "Saved as %s" %filename
    plt.savefig(filename)
    plt.close()

    # Leading coefficients for each label
    nlabels = len(pivots)
    fig, axarr = plt.subplots(nlabels, sharex=True)
    plt.xlabel(r"Wavelength $\lambda (\AA)$")
    plt.ticklabel_format(style='sci', axis='x', scilimits=(0,0))
    for i in range(nlabels):
        ax = axarr[i]
        ax.set_ylabel(r"$\theta_%s$" %(i+1))
        ax.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
        ax.set_title("First-Order Fit Coefficient for "+r"$%s$"%label_names[i])
        ax.plot(lams, coeffs_all[:,i+1], 
                label=r'$\theta_%s$' %(i+1)+"= the first-order fit coefficient")
        ax.legend(loc='upper right', prop={'family':'serif', 'size':'small'})
    print "Diagnostic plot: leading coefficients as a function of wavelength."
    filename = "leading_coeffs.png"
    print "Saved as %s" %filename
    fig.savefig(filename)
    plt.close(fig)

    # Histogram of the reduced chi squareds of the fits
    plt.hist(red_chisqs)
    plt.title("Distribution of Reduced Chi Squareds of the Model Fit")
    plt.ylabel("Count")
    plt.xlabel("Reduced Chi Sq") 
    filename = "modelfit_redchisqs.png"
    print "Diagnostic plot: histogram of the red chi squareds of the fit"
    print "Saved as %s" %filename
    plt.savefig(filename)
    plt.close()
