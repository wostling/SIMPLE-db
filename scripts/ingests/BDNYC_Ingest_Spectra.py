from scripts.ingests.utils import *
import pandas as pd
import numpy.ma as ma

SAVE_DB = False  # save the data files in addition to modifying the .db file
RECREATE_DB = True  # recreates the .db file from the data files
VERBOSE = False

logger.setLevel(logging.INFO)

db = load_simpledb('SIMPLE.db', recreatedb=RECREATE_DB)

# Read in CSV file as Astropy table
data = Table.read('scripts/ingests/BDNYC_spectra3.csv')


# Inserting various Libraries for Modes,Telescopes and Instruments
def insert_new_modes():
    telescope_mgl2 = [{'name': 'Magellan II Clay'}]
    instrument_mgl2 = [{'name': 'MagE'}]
    echelle2_mode = [{'name': 'Echelle',
                      'instrument': 'MagE',
                      'telescope': 'Magellan II Clay'}]
    # Inserting CTIO 1.5m
    telescope_ct = [{'name': 'CTIO 1.5m'}]
    instruments_ct = [{'name': 'OSIRIS'}]
    sxd_mode_ct = [{'name': 'SXD',
                    'instrument': 'OSIRIS',
                    'telescope': 'CTIO 1.5m'}]
    # Inserting LL Mode
    ll_mode = [{'name': 'LL',
                'instrument': 'IRS',
                'telescope': 'Spitzer'}]
    # Inserting Magellan I Baade
    telescope_mgl = [{'name': 'Magellan I Baade'}]
    instruments_mgl = [{'name': 'FIRE'}]
    echelle_mode = [{'name': 'Echelle',
                     'instrument': 'FIRE',
                     'telescope': 'Magellan I Baade'}]
    # Inserting IRS instrument and SL mode
    instrument_sl = [{'name': 'IRS'}]
    sxd_mode_sl = [{'name': 'SL',
                    'instrument': 'IRS',
                    'telescope': 'Spitzer'}]
    # Inserting Gemini South in various tables
    telescope_gmos = [{'name': 'Gemini South'}]
    instruments_gmos = [{'name': 'GMOS-S'}]
    prism_mode_gmos = [{'name': 'Prism',
                        'instrument': 'GMOS-S',
                        'telescope': 'Gemini South'}]
    # Inserting Gemini North in various tables
    telescope_gnirs = [{'name': 'Gemini North'}]
    instruments_gnirs = [{'name': 'GNIRS'}]
    sxd_mode_gnirs = [{'name': 'SXD',
                       'instrument': 'GNIRS',
                       'telescope': 'Gemini North'}]
    instrument_gmos_n = [{'name': 'GMOS-N'}]
    prism_mode_gmos_n = [{'name': 'Prism',
                          'instrument': 'GMOS-N',
                          'telescope': 'Gemini North'}]
    # Adding missing modes
    sxd_mode = [{'name': 'SXD',
                 'instrument': 'SpeX',
                 'telescope': 'IRTF'}]
    db.Telescopes.insert().execute(telescope_mgl2)
    db.Telescopes.insert().execute(telescope_ct)
    db.Telescopes.insert().execute(telescope_mgl)
    db.Telescopes.insert().execute(telescope_gmos)
    db.Telescopes.insert().execute(telescope_gnirs)
    db.Instruments.insert().execute(instrument_mgl2)
    db.Instruments.insert().execute(instruments_gmos)
    db.Instruments.insert().execute(instrument_sl)
    db.Instruments.insert().execute(instruments_mgl)
    db.Instruments.insert().execute(instruments_ct)
    db.Instruments.insert().execute(instrument_gmos_n)
    db.Instruments.insert().execute(instruments_gnirs)
    db.Modes.insert().execute(echelle2_mode)
    db.Modes.insert().execute(sxd_mode_ct)
    db.Modes.insert().execute(ll_mode)
    db.Modes.insert().execute(echelle_mode)
    db.Modes.insert().execute(sxd_mode_sl)
    db.Modes.insert().execute(prism_mode_gmos)
    db.Modes.insert().execute(prism_mode_gmos_n)
    db.Modes.insert().execute(sxd_mode_gnirs)
    db.Modes.insert().execute(sxd_mode)

    return


insert_new_modes()

source_names = data['designation']

missing_indices, existing_indices, alt_names_table = sort_sources(db, source_names)

#alt_names_string = 'BDNYC_ingest_spectra_alt_names.vot'
# alt_names_table.write(alt_names_string, format='votable')
#alt_names_table = Table.read(alt_names_string, format='votable')

add_names(db, names_table=alt_names_table)

# ADD MISSING SOURCES
to_add = data[missing_indices]
ingest_sources(db, to_add['designation'], to_add['ra'], to_add['dec'], to_add['publication_shortname'],
                comments=to_add['comments'])

missing_indices2, existing_indices2, alt_names_table2 = sort_sources(db, source_names)
existing_data = data[existing_indices2]

n_spectra = len(existing_data)
n_skipped = 0
n_added = 0
n_blank = 0

msg = f'Adding {n_spectra} spectra'
logger.info(msg)

for row in existing_data:
    # TODO: convert to function in utils
    # TODO: check that spectrum can be read by astrodbkit

    db_name = find_source_in_db(db, row['designation'])

    source_spec_data = db.query(db.Spectra).filter(db.Spectra.c.source == db_name).table()

    # SKIP if observation date is blank
    # TODO: try to populate obs date from meta data
    if ma.is_masked(row['obs_date']) or row['obs_date'] == '':
        obs_date = None
        missing_obs_msg = f"Skipping spectrum with missing observation date: {row['designation']} \n"
        missing_row_spe = f"{row['designation', 'name_1', 'mode', 'obs_date', 'publication_shortname']} \n"
        logger.info(missing_obs_msg)
        logger.debug(missing_row_spe)
        n_blank += 1
        continue
    else:
        obs_date = pd.to_datetime(row["obs_date"])

    publication_shortname = row["publication_shortname_1"]
    if publication_shortname == 'Alle07':
        publication_shortname = 'Alle07a'
    if publication_shortname == 'Wils03b':
        publication_shortname = 'Wils03'
    if publication_shortname == 'Kirk99':
        publication_shortname = 'Kirk99a'

    if len(source_spec_data) > 0:  # Spectra data already exists
        # check for duplicate measurement
        # TODO: Move to be as part of try/except
        ref_dupe_ind = source_spec_data['reference'] == publication_shortname
        date_dupe_ind = source_spec_data['observation_date'] == obs_date
        instrument_dupe_ind = source_spec_data['instrument'] == row['name_1']
        mode_dupe_ind = source_spec_data['mode'] == row['mode']
        file_dupe_ind = source_spec_data['spectrum'] == row['spectrum']
        if sum(ref_dupe_ind) and sum(date_dupe_ind) and sum(instrument_dupe_ind) and sum(mode_dupe_ind) and sum(file_dupe_ind):
            msg = f"Skipping suspected duplicate measurement \n"
            msg2 = f"{source_spec_data[ref_dupe_ind]['source', 'instrument', 'mode', 'observation_date', 'reference']}"
            msg3 = f"{row['designation', 'name_1', 'mode', 'obs_date', 'publication_shortname']} \n"
            logger.warning(msg + msg2 + msg3)
            n_skipped += 1
            continue  # Skip duplicate measurement

    row_data = [{'source': db_name,
                 'spectrum': row['spectrum'],
                 'local_spectrum': None if ma.is_masked(row["local_spectrum"]) else row["local_spectrum"],
                 'regime': row["regime"],
                 'telescope': row["name"],
                 'instrument': row["name_1"],
                 'mode': row["mode"],
                 'observation_date': obs_date,
                 'wavelength_units': None if ma.is_masked(row["wavelength_units"]) else row["wavelength_units"],
                 'flux_units': None if ma.is_masked(row["flux_units"]) else row["flux_units"],
                 'wavelength_order': None if ma.is_masked(row["wavelength_order"]) else row["wavelength_order"],
                 'comments': None if ma.is_masked(row["comments_1"]) else row["comments_1"],
                 'reference': publication_shortname}]
    logger.debug(row_data)

    try:
        db.Spectra.insert().execute(row_data)
        n_added += 1
    except sqlalchemy.exc.IntegrityError:
        msg = f"Spectrum could not be added to the database: \n {row_data} \n" \
              f"Reference may not exist in the Publications table."
        logger.error(msg)
        raise SimpleError(msg)

logger.info(f"Spectra added: {n_added}")
logger.info(f"Spectra skipped: {n_skipped}")
logger.info(f"Spectra with blank obs_date: {n_blank}")

if n_added + n_skipped + n_blank != n_spectra:
    msg = "Numbers don't add up: "
    logger.error(msg)
    raise SimpleError(msg)

# TODO: Count some spectra and add to tests