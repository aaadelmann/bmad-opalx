#!/Users/adelmann/git/opalx/.venv-h6/bin/python
"""Generate the local bend-comparison workspace under install/."""

from __future__ import annotations

from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent.parent
INSTALL_DIR = ROOT / 'install'
EXAMPLE_DIR = INSTALL_DIR / 'examples' / 'bend_compare'


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip())


def main() -> None:
    for directory in [
        EXAMPLE_DIR / 'data',
        EXAMPLE_DIR / 'output',
        EXAMPLE_DIR / 'figures',
        EXAMPLE_DIR / 'studies' / 'sbend_dt_convergence' / 'data',
        EXAMPLE_DIR / 'studies' / 'sbend_dt_convergence' / 'figures',
        EXAMPLE_DIR / 'studies' / 'sbend_dt_convergence' / 'work',
        EXAMPLE_DIR / 'studies' / 'sbend_bmad_sampling' / 'data',
        EXAMPLE_DIR / 'studies' / 'sbend_bmad_sampling' / 'figures',
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    write_file(EXAMPLE_DIR / 'sbend_proton_590MeV_45deg.bmad', """
        parameter[particle] = proton
        parameter[geometry] = open

        ! Proton kinetic energy = 590 MeV
        ! Total energy = m_p c^2 + E_kin = 1528.2720813 MeV
        beginning[e_tot] = 1.5282720813e9

        beginning[beta_a] = 1.0
        beginning[beta_b] = 1.0
        beginning[alpha_a] = 0.0
        beginning[alpha_b] = 0.0

        b1: sbend, l = 1.0, angle = pi/4, e1 = 0.0, e2 = 0.0, &
            fringe_type = none, tracking_method = runge_kutta, num_steps = 400

        line1: line = (b1)
        use, line1

        no_digested
        end_file
    """)

    write_file(EXAMPLE_DIR / 'rbend_electron_1GeV_45deg.bmad', """
        parameter[particle] = electron
        parameter[geometry] = open

        ! Electron kinetic energy = 1 GeV
        ! Total energy = m_e c^2 + E_kin = 1000.51099895 MeV
        beginning[e_tot] = 1.00051099895e9

        beginning[beta_a] = 1.0
        beginning[beta_b] = 1.0
        beginning[alpha_a] = 0.0
        beginning[alpha_b] = 0.0

        b1: rbend, l_rectangle = 1.0, angle = pi/4, e1 = 0.0, e2 = 0.0, &
            fiducial_pt = entrance_end, fringe_type = none, tracking_method = runge_kutta, num_steps = 400

        line1: line = (b1)
        use, line1

        no_digested
        end_file
    """)

    write_file(EXAMPLE_DIR / 'sbend_proton_590MeV_45deg_geometry.in', """
        &lattice_geometry_example_params
          lat_name = 'sbend_proton_590MeV_45deg.bmad'
        /
    """)

    write_file(EXAMPLE_DIR / 'rbend_electron_1GeV_45deg_geometry.in', """
        &lattice_geometry_example_params
          lat_name = 'rbend_electron_1GeV_45deg.bmad'
        /
    """)

    write_file(EXAMPLE_DIR / 'sbend_proton_590MeV_45deg_track.init', """
        &params
          lat_file = 'sbend_proton_590MeV_45deg.bmad'
          dat_file = 'output/sbend_proton_590MeV_45deg_track.dat'
          ix_branch = 0
          n_turn = 1
          start_orbit%vec = 0, 0, 0, 0, 0, 0
          start_orbit%spin = 0, 0, 1
          ran_seed = 1234
          write_track_at = 'ALL'
          bmad_com%radiation_damping_on = .false.
          bmad_com%radiation_fluctuations_on = .false.
          bmad_com%spin_tracking_on = .false.
          convert_from_prime_coords = .false.
          output_prime_coords = .false.
        /
    """)

    write_file(EXAMPLE_DIR / 'rbend_electron_1GeV_45deg_track.init', """
        &params
          lat_file = 'rbend_electron_1GeV_45deg.bmad'
          dat_file = 'output/rbend_electron_1GeV_45deg_track.dat'
          ix_branch = 0
          n_turn = 1
          start_orbit%vec = 0, 0, 0, 0, 0, 0
          start_orbit%spin = 0, 0, 1
          ran_seed = 1234
          write_track_at = 'ALL'
          bmad_com%radiation_damping_on = .false.
          bmad_com%radiation_fluctuations_on = .false.
          bmad_com%spin_tracking_on = .false.
          convert_from_prime_coords = .false.
          output_prime_coords = .false.
        /
    """)

    write_file(EXAMPLE_DIR / 'opalx_proton_distribution.txt', """
        1
        x px y py z pz
        0.0 0.0 0.0 0.0 0.0 1.2857059679563454
    """)

    write_file(EXAMPLE_DIR / 'opalx_electron_distribution.txt', """
        1
        x px y py z pz
        0.0 0.0 0.0 0.0 0.0 1957.9509281901853
    """)

    write_file(EXAMPLE_DIR / 'sbend_proton_590MeV_45deg_opalx.in', """
        OPTION, PSDUMPFREQ = 50000;
        OPTION, STATDUMPFREQ = 1;
        OPTION, BOUNDPDESTROY = 10;
        OPTION, VERSION = 10900;

        Title, string = "OPALX proton SBEND comparison case";

        B1: SBEND, L = 1.0, ANGLE = PI / 4, ELEMEDGE = 0.0;

        Line1: Line = (B1);

        Dist0: DISTRIBUTION,
            TYPE = FROMFILE,
            FNAME = "opalx_proton_distribution.txt",
            NPARTDIST = 1;

        ES0: EMISSIONSOURCE, DISTRIBUTION = Dist0;
        Sources0: EMISSIONSOURCELIST = (ES0);

        FS0: FIELDSOLVER,
            TYPE = NONE,
            NX = 16,
            NY = 16,
            NZ = 16,
            PARFFTX = false,
            PARFFTY = false,
            PARFFTZ = true,
            BCFFTX = open,
            BCFFTY = open,
            BCFFTZ = open,
            BBOXINCR = 1,
            GREENSF = INTEGRATED;

        BEAM0: BEAM,
            PARTICLE = PROTON,
            NALLOC = 1,
            BCHARGE = 1.6021766339999998e-19,
            SOURCES = Sources0,
            CHARGE = 1;

        TRACK,
            LINE = Line1,
            BEAM = BEAM0,
            MAXSTEPS = 10000,
            DT = 1e-10,
            ZSTOP = 1.2;

        RUN,
            METHOD = "PARALLEL",
            FIELDSOLVER = FS0;

        ENDTRACK;

        QUIT;
    """)

    write_file(EXAMPLE_DIR / 'rbend_electron_1GeV_45deg_opalx.in', """
        OPTION, PSDUMPFREQ = 50000;
        OPTION, STATDUMPFREQ = 1;
        OPTION, BOUNDPDESTROY = 10;
        OPTION, VERSION = 10900;

        Title, string = "OPALX electron RBEND comparison case";

        B1: RBEND, L = 1.082392200292394, ANGLE = PI / 4, ELEMEDGE = 0.0;

        Line1: Line = (B1);

        Dist0: DISTRIBUTION,
            TYPE = FROMFILE,
            FNAME = "opalx_electron_distribution.txt",
            NPARTDIST = 1;

        ES0: EMISSIONSOURCE, DISTRIBUTION = Dist0;
        Sources0: EMISSIONSOURCELIST = (ES0);

        FS0: FIELDSOLVER,
            TYPE = NONE,
            NX = 16,
            NY = 16,
            NZ = 16,
            PARFFTX = false,
            PARFFTY = false,
            PARFFTZ = true,
            BCFFTX = open,
            BCFFTY = open,
            BCFFTZ = open,
            BBOXINCR = 1,
            GREENSF = INTEGRATED;

        BEAM0: BEAM,
            PARTICLE = ELECTRON,
            NALLOC = 1,
            BCHARGE = 1.6021766339999998e-19,
            SOURCES = Sources0,
            CHARGE = -1;

        TRACK,
            LINE = Line1,
            BEAM = BEAM0,
            MAXSTEPS = 10000,
            DT = 1e-12,
            ZSTOP = 1.2;

        RUN,
            METHOD = "PARALLEL",
            FIELDSOLVER = FS0;

        ENDTRACK;

        QUIT;
    """)

    print(f'Prepared bend-comparison workspace under {EXAMPLE_DIR}')


if __name__ == '__main__':
    main()
