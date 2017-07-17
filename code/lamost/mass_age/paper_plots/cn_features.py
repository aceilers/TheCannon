""" Plot the carbon and nitrogen theoretical gradient spectra,
overlaid with our "gradient spectra" from The Cannon """

import numpy as np
import matplotlib.pyplot as plt
import pyfits
import copy
from matplotlib import rc
rc('font', family='serif')
rc('text', usetex=True)
from matplotlib import cm
from matplotlib.colors import LogNorm
from TheCannon import train_model
from TheCannon import continuum_normalization


def normalize(spec):
    """ Normalize according to Martell et al 2008
    That is to say, spectra are normalized at 4319.2 Angstroms
    """
    return spec / spec[344]


def cannon_normalize(spec_raw):
    """ Normalize according to The Cannon """
    spec = np.array([spec_raw])
    wl = np.arange(0, spec.shape[1])
    w = continuum_normalization.gaussian_weight_matrix(wl, L=50)
    ivar = np.ones(spec.shape)*0.5
    cont = continuum_normalization._find_cont_gaussian_smooth(
            wl, spec, ivar, w)
    norm_flux, norm_ivar = continuum_normalization._cont_norm(
            spec, ivar, cont)
    return norm_flux[0]


def plot_cannon(ax, wl, grad_spec):
    ax.plot(
            wl, grad_spec, c='black', label="Cannon Gradient Spectrum", 
            linewidth=1, drawstyle='steps-mid')
    ax.legend(loc='lower left')
    ax.tick_params(axis='x', labelsize=16)
    ax.tick_params(axis='y', labelsize=16)


def plot_model(ax, wl, grad_spec):
    ax.plot(
            wl, grad_spec, c='red', label="Theoretical Gradient Spectrum", 
            linewidth=0.5, drawstyle='steps-mid')#, linestyle='-')
    ax.legend(loc='lower left')
    ax.tick_params(axis='x', labelsize=16)
    ax.tick_params(axis='y', labelsize=16)


def gen_cannon_grad_spec(base_labels, choose, low, high, coeffs, pivots):
    """ Generate Cannon gradient spectra

    Parameters
    ----------
    labels: default values for [teff, logg, feh, cfe, nfe, afe, ak]
    choose: val of cfe or nfe, whatever you're varying
    low: lowest val of cfe or nfe, whatever you're varying
    high: highest val of cfe or nfe, whatever you're varying
    """
    # Generate Cannon gradient spectra
    low_lab = copy.copy(base_labels)
    low_lab[choose] = low
    lvec = (train_model._get_lvec(np.array([low_lab]), pivots))[0]
    model_low = np.dot(coeffs, lvec)
    high_lab = copy.copy(base_labels)
    high_lab[choose] = high
    lvec = (train_model._get_lvec(np.array([high_lab]), pivots))[0]
    model_high = np.dot(coeffs, lvec)
    grad_spec = (model_high - model_low) / (high - low)
    return grad_spec


def get_model_spec_martell():
    # Carbon and nitrogen theoretical gradient spectra
    DATA_DIR = "/Users/annaho/Data/Martell"
    inputf = "ssg_wv.fits"
    a = pyfits.open(DATA_DIR + "/" + inputf)
    wl = a[1].data
    a.close()

    inputf = "ssg_nowv.fits"
    a = pyfits.open(DATA_DIR + "/" + inputf)
    dat = a[1].data
    a.close()

    ind = np.where(np.logical_and(dat['Nfe']==0.6, dat['FeH']==-1.41))[0]
    cfe = dat['cfe'][ind]
    # only step from -0.4 to 0.4
    #dflux = cannon_normalize(dat[ind[-1]][3])-cannon_normalize(dat[ind[0]][3])
    dflux = cannon_normalize(dat[ind[9]][3])-cannon_normalize(dat[ind[5]][3])
    #dcfe = cfe[1]-cfe[0]
    dcfe = cfe[9]-cfe[5]
    c_grad_spec = (dflux/dcfe)

    ind = np.where(np.logical_and(dat['cfe']==-0.4, dat['FeH']==-1.41))[0]
    nfe = dat['nfe'][ind]
    # only step from -0.4 to 0.4
    dflux = cannon_normalize(dat[ind[5]][3])-cannon_normalize(dat[ind[1]][3])
    dnfe = nfe[5]-nfe[1]
    n_grad_spec = (dflux/dnfe)
    
    return wl, c_grad_spec, n_grad_spec


def get_model_spec_ting(atomic_number):
    """ 
    X_u_template[0:2] are teff, logg, vturb in km/s
    X_u_template[:,3] -> onward, put atomic number 
    atomic_number is 6 for C, 7 for N
    """
    DATA_DIR = "/Users/annaho/Data/LAMOST/Mass_And_Age"
    temp = np.load("%s/X_u_template_KGh_res=1800.npz" %DATA_DIR)
    X_u_template = temp["X_u_template"]
    wl = temp["wavelength"]
    if atomic_number == 6:
        print("Plotting Carbon")
    elif atomic_number == 7:
        print("Plotting Nitrogen")
    grad_spec = X_u_template[:,atomic_number]
    return wl, cannon_normalize(grad_spec+1)


def plot_cn(my_wl, c_grad_spec, n_grad_spec, wl, c_grad_model, n_grad_model):
    # Make a plot
    fig, axarr = plt.subplots(ncols=2, figsize=(12,6), 
                                  sharex=True, sharey=True)
    ax0 = axarr[0]
    ax1 = axarr[1]
    plt.subplots_adjust(wspace=0.1)
    props = dict(boxstyle='round', facecolor='white')
    x = 0.05
    y = 0.92
    ax0.text(
            x, y, 
            #r"-0.3 \textless [C/Fe] \textless 0.3", 
            "Carbon", bbox=props,
            transform=ax0.transAxes, fontsize=16)
    ax1.text(x, y, 
            #r"-0.4 \textless [N/Fe] \textless 0.4", 
            "Nitrogen", bbox=props,
            transform=ax1.transAxes, fontsize=16)

    # Label some of the molecular absorption features
    for ax in axarr: 
        ax.text(
                0.25, 0.80, 
                "CN band", 
                transform=ax.transAxes, fontsize=16)
    ax0.text(
            0.65, 0.92,
            "G band (CH)",
            transform=ax0.transAxes, fontsize=16)



    plot_cannon(ax0, my_wl, c_grad_spec)
    plot_cannon(ax1, my_wl, n_grad_spec)

    plot_model(ax0, wl, c_grad_model-1)
    plot_model(ax1, wl, n_grad_model-1)

    ax0.set_xlim(4050,4400)
    ax1.set_xlim(4050, 4400)
    ax0.set_ylim(-0.6, 0.4)
    ax1.set_ylim(-0.6, 0.4)
    ax0.set_xlabel(r"Wavelength $\lambda (\AA)$", fontsize=18)
    ax1.set_xlabel(r"Wavelength $\lambda (\AA)$", fontsize=18)
    ax0.set_ylabel("Normalized Flux", fontsize=18)
    #ax0.axvline(x=4310, c='r')
    #ax1.axvline(x=4310, c='r')

    #plt.show()
    plt.savefig("cn_features.png")


if __name__=="__main__":
    DATA_DIR = "/Users/annaho/Data/LAMOST/Mass_And_Age/with_col_mask/training_step"
    my_wl = np.load(DATA_DIR + "/" + "wl_cols.npz")['arr_0']

    m_coeffs = np.load(DATA_DIR + "/" + "coeffs.npz")['arr_0']
    m_pivots = np.load(DATA_DIR + "/" + "pivots.npz")['arr_0']
    m_scatters = np.load(DATA_DIR + "/" + "scatters.npz")['arr_0']

    # Yuan-Sen: K giant, teff = 4750, logg=2.5, [X/H] = 0.0
    # dteff = 200K, dlogg = 0.5, dXH = 0.2
    labels = [4750, 2.5, 0.0, 0.0, 0.0, 0.0, 0.0]
    c_grad_spec = gen_cannon_grad_spec(
            labels, 3, 0.0, 0.2, m_coeffs, m_pivots) 
    n_grad_spec = gen_cannon_grad_spec(
            labels, 4, 0.0, 0.2, m_coeffs, m_pivots) 

    #wl, c_grad_model = get_model_spec_ting(6)
    #wl, n_grad_model = get_model_spec_ting(7)

    readf = "/Users/annaho/Data/LAMOST/ting_model_spec.npz"
    wl = np.load(readf)['wavelength']
    ref = np.load(readf)['flux_spectra'][99,:] 
    c_dat = np.load(readf)['flux_spectra'][6,:]
    c_grad_model = (cannon_normalize(c_dat)-cannon_normalize(ref))/0.2 + 1
    n_dat = np.load(readf)['flux_spectra'][7,:]
    n_grad_model = (cannon_normalize(n_dat)-cannon_normalize(ref))/0.2 + 1

    plot_cn(my_wl, c_grad_spec, n_grad_spec, wl, c_grad_model, n_grad_model)
    #wl, c_grad_model, n_grad_model = get_model_spec_martell()


