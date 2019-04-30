import pytest

import fair
from fair.RCPs import rcp3pd, rcp45, rcp6, rcp85
from fair.tools import magicc, steady, ensemble
from fair.constants import molwt, lifetime, radeff
from fair.constants.general import M_ATMOS
import numpy as np
import os


def test_no_arguments():
    with pytest.raises(ValueError):
        fair.forward.fair_scm()


def test_scenfile():
    datadir = os.path.join(os.path.dirname(__file__), 'rcp45/')
    # Purpose of this test is to determine whether the SCEN file for RCP4.5
    # which does not include CFCs, years before 2000, or emissions from every
    # year from 2000 to 2500, equals the emissions file from RCP4.5
    # after reconstruction.
    # The .SCEN and .XLS files at http://www.pik-potsdam.de/~mmalte/rcps
    # sometimes differ in the 4th decimal place. Thus we allow a tolerance of
    # 0.0002 in addition to machine error in this instance.

    E1 = magicc.scen_open(datadir + 'RCP45.SCEN')
    assert np.allclose(E1, rcp45.Emissions.emissions, rtol=1e-8, atol=2e-4)

    E2 = magicc.scen_open(datadir + 'RCP45.SCEN', include_cfcs=False)
    assert np.allclose(E2, rcp45.Emissions.emissions[:,:24], rtol=1e-8,
        atol=2e-4)

    E3 = magicc.scen_open(datadir + 'RCP45.SCEN', startyear=1950)
    assert np.allclose(E3, rcp45.Emissions.emissions[185:,:], rtol=1e-8,
        atol=2e-4)

    # Test `_import_emis_file`
    assert magicc._import_emis_file('rcp26') == rcp3pd.Emissions
    assert magicc._import_emis_file('rcp6') == rcp6.Emissions
    assert magicc._import_emis_file('rcp85') == rcp85.Emissions
    with pytest.raises(ValueError):
        magicc._import_emis_file('rcp19')

    test_files = os.path.join(os.path.dirname(__file__), "scenfiles")
    scenfile_2000 = os.path.join(test_files, "WORLD_ONLY.SCEN")
    scenfile_2010 = os.path.join(test_files, "WORLD_ONLY_2010.SCEN")

    # Test CFCs inclusion.
    with pytest.raises(ValueError):
        magicc.scen_open(datadir + 'RCP45.SCEN', include_cfcs=np.zeros(0))
    E4 = magicc.scen_open(
            scenfile_2000, startyear=2000, include_cfcs=np.ones((51, 16)))
    assert E4[0, -1] == 1
    with pytest.raises(ValueError):
        magicc.scen_open(datadir + 'RCP45.SCEN', include_cfcs="foo")

    # Test filling of history and harmonisation.
    with pytest.raises(ValueError):
        magicc.scen_open(scenfile_2010)
    with pytest.raises(ValueError):
        magicc.scen_open(scenfile_2000, harmonise=1950)
    with pytest.raises(ValueError):
        magicc.scen_open(scenfile_2000, harmonise=2060)
    E5 = magicc.scen_open(scenfile_2000, harmonise=2010)
    assert E5[0, 1] == rcp45.Emissions.co2_fossil[0]


def test_steady():
    assert np.isclose(steady.emissions(species='CH4'), 209.2492053169677)
    assert np.isclose(steady.emissions(species='N2O'), 11.155476818389447)
    assert np.isclose(steady.emissions(species='CF4'), 0.010919593149304725)
    assert steady.emissions(species='CFC11')==0.
    assert np.isclose(steady.emissions(species='CH4', lifetime=12.4), 
      159.0269945578832)
    assert np.isclose(steady.emissions(species='CH4', molwt=17),
      221.77284852795833)
    assert np.isclose(steady.emissions(species='CH4', C=1750.),
      507.2573722823332)
    # verify override working
    assert steady.emissions(species='CH4', lifetime=12.4, molwt=17, 
      C=1750.) != steady.emissions(species='CH4')
    # not a gas on the list - should report error
    with pytest.raises(ValueError):
        steady.emissions(species='chocolate')
    # and no input equals no output, so again value error
    with pytest.raises(ValueError):
        steady.emissions()


def test_restart_co2_continuous():
    # Tests to check that a CO2-only run with a restart produces the same
    # results as a CO2-only run without a restart.
    
    C, F, T = fair.forward.fair_scm(
        emissions   = rcp45.Emissions.co2[:20],
        useMultigas = False
        )
        
    C1, F1, T1, restart = fair.forward.fair_scm(
        emissions   = rcp45.Emissions.co2[:10],
        useMultigas = False,
        restart_out = True
        )

    C2, F2, T2 = fair.forward.fair_scm(
        emissions   = rcp45.Emissions.co2[10:20],
        useMultigas = False,
        restart_in  = restart
        )
        
    assert np.all(C == np.concatenate((C1, C2)))
    assert np.all(F == np.concatenate((F1, F2)))
    assert np.all(T == np.concatenate((T1, T2)))


def test_ensemble_generator():
    """This test determines whether the ensemble generator is behaving as
    expected."""

    # load up the CMIP5 TCR and ECS values
    infile = os.path.join(os.path.dirname(__file__),
      '../../fair/tools/tcrecs/cmip5tcrecs.csv')
    cmip5_tcrecs = np.loadtxt(infile, skiprows=3, delimiter=',')
    cmip5_tcr_mean = np.mean(cmip5_tcrecs[:,0])
    cmip5_ecs_mean = np.mean(cmip5_tcrecs[:,1])
    cmip5_tcr_std  = np.std(cmip5_tcrecs[:,0])
    cmip5_ecs_std  = np.std(cmip5_tcrecs[:,1])
    cmip5_corrcoef = np.corrcoef(cmip5_tcrecs[:,0], cmip5_tcrecs[:,1])[1,0]

    # generate 1000 random values with these inputs. Set strip to False
    # so that overall statistics are not affected and more comparable with
    # input data
    ensgen_tcrecs = ensemble.tcrecs_generate(seed=0, strip_ecs_lt_tcr=False)
    ensgen_tcr_mean = np.mean(ensgen_tcrecs[:,0])
    ensgen_ecs_mean = np.mean(ensgen_tcrecs[:,1])
    ensgen_tcr_std  = np.std(ensgen_tcrecs[:,0])
    ensgen_ecs_std  = np.std(ensgen_tcrecs[:,1])
    ensgen_corrcoef = np.corrcoef(ensgen_tcrecs[:,0], ensgen_tcrecs[:,1])[1,0]

    # check generated values match cmip5 stats to within 5%
    # possibly too generous but should catch variance v stdev errors
    assert 0.95 < ensgen_tcr_mean/cmip5_tcr_mean < 1.05
    assert 0.95 < ensgen_tcr_std/cmip5_tcr_std < 1.05
    assert 0.95 < ensgen_ecs_mean/cmip5_ecs_mean < 1.05
    assert 0.95 < ensgen_ecs_std/cmip5_ecs_std < 1.05
    assert 0.95 < ensgen_corrcoef/cmip5_corrcoef < 1.05

    # check changing seed changes distribution
    ensgen_tcrecs1 = ensemble.tcrecs_generate(seed=1, strip_ecs_lt_tcr=False)
    assert np.any(ensgen_tcrecs1 != ensgen_tcrecs)

    # check uncorrelated distribution
    ensgen_tcrecs = ensemble.tcrecs_generate(seed=0, correlated=False)
    assert 0.95 < ensgen_tcr_mean/cmip5_tcr_mean < 1.05
    assert 0.95 < ensgen_tcr_std/cmip5_tcr_std < 1.05
    assert 0.95 < ensgen_ecs_mean/cmip5_ecs_mean < 1.05
    assert 0.95 < ensgen_ecs_std/cmip5_ecs_std < 1.05
    assert (-0.10 < 
      np.corrcoef(ensgen_tcrecs[:,0], ensgen_tcrecs[:,1])[1,0] 
      < 0.10)

    # check normal distribution assumption
    ensgen_tcrecs = ensemble.tcrecs_generate(seed=0,
      strip_ecs_lt_tcr=False, dist='norm')
    ensgen_tcr_mean = np.mean(ensgen_tcrecs[:,0])
    ensgen_ecs_mean = np.mean(ensgen_tcrecs[:,1])
    ensgen_tcr_std  = np.std(ensgen_tcrecs[:,0])
    ensgen_ecs_std  = np.std(ensgen_tcrecs[:,1])
    assert 0.95 < ensgen_tcr_mean/cmip5_tcr_mean < 1.05
    assert 0.95 < ensgen_tcr_std/cmip5_tcr_std < 1.05
    assert 0.95 < ensgen_ecs_mean/cmip5_ecs_mean < 1.05
    assert 0.95 < ensgen_ecs_std/cmip5_ecs_std < 1.05
    assert 0.95 < ensgen_corrcoef/cmip5_corrcoef < 1.05

    # check normal, correlated
    ensgen_tcrecs = ensemble.tcrecs_generate(seed=0, correlated=False,
      dist='norm')
    assert 0.95 < ensgen_tcr_mean/cmip5_tcr_mean < 1.05
    assert 0.95 < ensgen_tcr_std/cmip5_tcr_std < 1.05
    assert 0.95 < ensgen_ecs_mean/cmip5_ecs_mean < 1.05
    assert 0.95 < ensgen_ecs_std/cmip5_ecs_std < 1.05
    assert (-0.10 <
      np.corrcoef(ensgen_tcrecs[:,0], ensgen_tcrecs[:,1])[1,0]
      < 0.10)


def test_iirf():
    """Test that changing the time horizon of time-integrated airborne
    fraction makes a material difference to the carbon cycle."""

    # default case
    C1,F1,T1 = fair.forward.fair_scm(
      emissions=rcp85.Emissions.co2,
      useMultigas=False,
    )

    # set iirf_h = 100: should be same as default case
    C2,F2,T2 = fair.forward.fair_scm(
      emissions=rcp85.Emissions.co2,
      useMultigas=False,
      iirf_h = 100
    )

    # vary iirf_h and expect differences to the 100-year case.
    # Want a warning to flag that iirf_max > iirf_h
    with pytest.warns(RuntimeWarning):
        C3,F3,T3 = fair.forward.fair_scm(
          emissions=rcp85.Emissions.co2,
          useMultigas=False,
          iirf_h = 60
        )

    # Run again limiting iirf_max. Check output differs to the case above.
    # For RCP8.5 this should happen much beyond present-day concentrations.
    C4,F4,T4 = fair.forward.fair_scm(
      emissions=rcp85.Emissions.co2,
      useMultigas=False,
      iirf_h = 60,
      iirf_max = 58
    )

    assert np.all(C1==C2)
    assert np.all(F1==F2)
    assert np.all(T1==T2)
    assert np.any(C2!=C4)
    assert np.any(F2!=F4)
    assert np.any(T2!=T4)
    assert np.any(C3!=C4)
    assert np.any(F3!=F4)
    assert np.any(T3!=T4)


def test_q():
    """Test that separating out the q-calculation function does not affect
    results, and that both constant and time-varying values work.

    If no other tests break, then this is integrated correctly."""

    # constant ecs and tcr
    nt      = 10
    tcrecs  = np.array([1.75, 3.0])
    d       = np.array([4.1, 239.0])
    f2x     = 3.71
    tcr_dbl = np.log(2.)/np.log(1.01)
    q       = fair.forward.calculate_q(tcrecs, d, f2x, tcr_dbl, nt)
    assert q.shape==(nt, 2)
    assert np.all(q[:,0]==np.mean(q[:,0])) # check tcr and ecs constant
    assert np.all(q[:,1]==np.mean(q[:,1]))

    # time-varying ecs and tcr
    tcrecs  = np.empty((nt, 2))
    tcrecs[:,0] = np.linspace(1.65, 1.85, nt)
    tcrecs[:,1] = np.linspace(2.8, 4.0, nt)
    q       = fair.forward.calculate_q(tcrecs, d, f2x, 70., nt)
    assert q.shape==(nt, 2)
    assert np.any(q[:,0]!=np.mean(q[:,0]))
    assert np.any(q[:,1]!=np.mean(q[:,1]))

    # are errors handled? 
    tcrecs  = np.array([1.75, 3.0, np.pi])
    with pytest.raises(ValueError):
        q = fair.forward.calculate_q(tcrecs, d, f2x, tcr_dbl, nt)
    tcrecs  = np.empty((nt, 2))
    tcrecs[:,0] = np.linspace(1.65, 1.85, nt)
    tcrecs[:,1] = np.linspace(2.8, 4.0, nt)
    with pytest.raises(ValueError):
        q = fair.forward.calculate_q(tcrecs, d, f2x, tcr_dbl, nt+1)


def test_iirf_simple():
    r0 = 35
    rc = 0.019
    rt = 4.165
    iirf_max = 97
    c_acc = 1000.
    temp = 1.5

    iirf = fair.forward.iirf_simple(c_acc, temp, r0, rc, rt, iirf_max)
    assert iirf == r0 + rc*c_acc + rt*temp


def test_iirf_simple_max():
    r0 = 35
    rc = 0.019
    rt = 4.165
    c_acc = 1000.
    temp = 1.5
    iirf = fair.forward.iirf_simple(c_acc, temp, r0, rc, rt, 32)
    assert iirf == 32


def test_emis_to_conc():
    c0 = 1000.
    e0 = 300.
    e1 = 310.
    ts = 1.
    lt = 9.3
    vm = 2.123
    c1 = fair.forward.emis_to_conc(c0, e0, e1, ts, lt, vm)
    assert c1 == c0 - c0 * (1.0 - np.exp(-ts/lt)) + 0.5 * ts * (e1 + e0) * vm
    
    
def test_carbon_cycle():
    """Test the stand-alone carbon cycle component of FaIR"""
    # TODO: put defaults into a module
    e0 = 10.
    c_acc0 = 0.
    temp = 0.
    r0 = 35.
    rc = 0.019
    rt = 4.165
    iirf_max = 97.
    iirf_guess = 0.16
    a = np.array([0.2173,0.2240,0.2824,0.2763])
    tau = np.array([1000000,394.4,36.54,4.304])
    iirf_h = 100
    carbon_boxes0 = np.zeros(4)
    ppm_gtc = M_ATMOS/1e18*molwt.C/molwt.AIR
    c0 = 0.
    e1 = 10.
    c1, c_acc1 = fair.forward.carbon_cycle(
      e0, c_acc0, temp, r0, rc, rt, iirf_max, iirf_guess, a, tau, iirf_h,
      carbon_boxes0, ppm_gtc, c0, e1)
    c_full, f_full, t_full = fair.forward.fair_scm(
      emissions=np.ones(1)*10, useMultigas=False)
    c_pi = 278.
    assert c_full==c1+c_pi