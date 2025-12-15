# %% [markdown]
# # Paris Data Processing: 2015 & 2019 Snapshot
# **Goal:** Create a strict dataset for 2015 and 2019 with no interpolation.

# %%
import pandas as pd
import numpy as np
from pathlib import Path
import geopandas as gpd
import warnings

warnings.filterwarnings('ignore')

# --- CONFIG ---
BASE_DIR = Path("../data/raw/paris")
OUTPUT_DIR = Path("../data/preprocessed/paris")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# We only care about these two years
TARGET_YEARS = [2015, 2019]

# %% [markdown]
# ## 1. Helper Functions (Robust Loader)

# %%
def get_quartier_id_from_iris(iris_code):
    # Standardize IRIS to Quartier ID
    s = str(iris_code).strip().split('.')[0]
    if len(s) >= 7:
        return 'PARIS_' + s[:7]
    return None

def find_header_and_sep(filepath, encodings=['utf-8', 'latin-1', 'windows-1252']):
    """Scans file to find the real header row containing 'IRIS'"""
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                lines = [f.readline() for _ in range(30)]
            for i, line in enumerate(lines):
                for sep in [';', ',']:
                    # Clean the line and check for IRIS keyword
                    clean_line = line.upper().replace('"', '')
                    if 'IRIS' in clean_line.split(sep) or 'CODE_IRIS' in clean_line.split(sep):
                        return i, sep, enc
        except:
            continue
    return 0, ';', 'utf-8' # Fallback

def load_insee_csv(filepath):
    path = Path(filepath)
    if not path.exists(): 
        print(f"❌ File not found: {path.name}")
        return None
    
    skip, sep, enc = find_header_and_sep(path)
    try:
        df = pd.read_csv(path, sep=sep, skiprows=skip, encoding=enc, dtype=str, low_memory=False)
        # Uppercase and clean columns
        df.columns = [c.upper().strip().strip('"') for c in df.columns]
        
        # Normalize IRIS column name
        iris_col = next((c for c in df.columns if c in ['IRIS', 'CODE_IRIS', 'IRIS_GEO']), None)
        if iris_col:
            df.rename(columns={iris_col: 'IRIS'}, inplace=True)
            return df
    except Exception as e:
        print(f"❌ Failed to read {path.name}: {e}")
    return None

# %% [markdown]
# ## 2. Build Backbone (80 Neighborhoods x 2 Years)

# %%
print("--- Building Geometry Backbone ---")
quartiers_gdf = gpd.read_file(BASE_DIR / "quartier_paris.geojson")
quartiers_gdf['neighborhood_id'] = 'PARIS_' + quartiers_gdf['c_quinsee'].astype(str)
quartiers_gdf['area_km2'] = quartiers_gdf.to_crs(epsg=2154).geometry.area / 1_000_000

# Create the master list of rows we expect
backbone_rows = []
for nid in quartiers_gdf['neighborhood_id'].unique():
    for y in TARGET_YEARS:
        backbone_rows.append({'neighborhood_id': nid, 'year': y})

master_df = pd.DataFrame(backbone_rows)
print(f"✅ Created Backbone: {len(master_df)} rows ({len(quartiers_gdf)} Neighborhoods * {len(TARGET_YEARS)} Years)")

# %% [markdown]
# ## 3. Process Real Estate (2015 & 2019 Specifics)

# %%
print("\n--- Processing DVF (Prices) ---")
dvf_dfs = []

# We now look for the specific files we downloaded in Step 0
for year in TARGET_YEARS:
    filename = f"dvf_75_{year}.csv.gz"
    path = BASE_DIR / "household prices" / filename
    
    if path.exists():
        print(f"  Loading {filename}...")
        try:
            # Load only necessary columns
            df = pd.read_csv(
                path, 
                usecols=['date_mutation', 'valeur_fonciere', 'surface_reelle_bati', 'longitude', 'latitude', 'type_local', 'nature_mutation'],
                dtype={'valeur_fonciere': float, 'surface_reelle_bati': float},
                low_memory=False
            )
            
            # Filter
            mask = (
                (df['nature_mutation'] == 'Vente') &
                (df['type_local'] == 'Appartement') &
                (df['valeur_fonciere'] > 5000) &
                (df['surface_reelle_bati'] > 9)
            )
            df = df[mask].copy()
            
            # Metric
            df['price_per_m2'] = df['valeur_fonciere'] / df['surface_reelle_bati']
            df = df[df['price_per_m2'].between(1000, 50000)] # Paris specific cap
            
            # Create GeoDataFrame
            gdf_sales = gpd.GeoDataFrame(
                df, 
                geometry=gpd.points_from_xy(df.longitude, df.latitude),
                crs="EPSG:4326"
            )
            
            # Spatial Join
            joined = gpd.sjoin(gdf_sales, quartiers_gdf[['neighborhood_id', 'geometry']], predicate='within')
            
            # Aggregate
            agg = joined.groupby('neighborhood_id')['price_per_m2'].median().reset_index()
            agg.rename(columns={'price_per_m2': 'median_price_per_m2'}, inplace=True)
            agg['year'] = year
            dvf_dfs.append(agg)
            print(f"    -> Found {len(agg)} neighborhoods with sales data.")
            
        except Exception as e:
            print(f"    -> Error processing {year}: {e}")
    else:
        print(f"❌ Missing DVF file for {year}. Did you run the download cell?")

if dvf_dfs:
    dvf_final = pd.concat(dvf_dfs, ignore_index=True)
else:
    dvf_final = pd.DataFrame(columns=['neighborhood_id', 'year', 'median_price_per_m2'])

# %% [markdown]
# ## 4. Process Socio-Economic (Strict Mapping)

# %%
print("\n--- Processing Socio-Economic Data ---")

# --- POPULATION ---
# 2015: P15_POP, P15_POP1824, P15_POP2539
# 2019: P19_POP, P19_POP1824, P19_POP2539
pop_config = [
    (2015, BASE_DIR / "POPULATION/base-ic-evol-struct-pop-2015_csv/base-ic-evol-struct-pop-2015.csv"),
    (2019, BASE_DIR / "POPULATION/base-ic-evol-struct-pop-2019_csv/base-ic-evol-struct-pop-2019.CSV")
]

pop_results = []
for year, path in pop_config:
    df = load_insee_csv(path)
    if df is not None:
        yy = str(year)[-2:]
        
        # Mappings
        col_total = f'P{yy}_POP'
        col_1824 = f'P{yy}_POP1824'
        col_2539 = f'P{yy}_POP2539'
        
        # Check columns existence
        if col_total in df.columns:
            # Clean
            for c in [col_total, col_1824, col_2539]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c].str.replace(',', '.'), errors='coerce').fillna(0)
            
            # Calc Logic
            df['neighborhood_id'] = df['IRIS'].apply(get_quartier_id_from_iris)
            df = df.dropna(subset=['neighborhood_id'])
            
            # Group
            agg = df.groupby('neighborhood_id')[[col_total, col_1824, col_2539]].sum().reset_index()
            agg['young_adults_pop'] = agg[col_1824] + agg[col_2539]
            agg.rename(columns={col_total: 'total_pop'}, inplace=True)
            agg = agg[['neighborhood_id', 'total_pop', 'young_adults_pop']]
            agg['year'] = year
            pop_results.append(agg)
            print(f"  Population {year}: Ready ({len(agg)} neighborhoods)")

if pop_results:
    pop_final = pd.concat(pop_results, ignore_index=True)
else:
    pop_final = pd.DataFrame()

# --- INCOME ---
# 2015: Usually 'DEC_MED15' (Declared Income) or 'DISP_MED15' (Disposable)
# 2019: 'DISP_MED19'
inc_config = [
    (2015, BASE_DIR / "Income, poverty and standard of living/BASE_TD_FILO_IRIS_2015_DEC_CSV/Hoja de cálculo sin título - IRIS_DEC.csv"),
    (2019, BASE_DIR / "Income, poverty and standard of living/BASE_TD_FILO_IRIS_2019_DEC_CSV/BASE_TD_FILO_DEC_IRIS_2019.csv")
]

inc_results = []
for year, path in inc_config:
    df = load_insee_csv(path)
    if df is not None:
        yy = str(year)[-2:]
        
        # Attempt to find the correct column
        candidates = [f'DISP_MED{yy}', f'DEC_MED{yy}', 'DEC_MED15', 'DISP_MED15']
        target_col = next((c for c in candidates if c in df.columns), None)
        
        if target_col:
            # Clean
            df[target_col] = pd.to_numeric(df[target_col].str.replace(',', '.').str.replace(' ', ''), errors='coerce')
            
            df['neighborhood_id'] = df['IRIS'].apply(get_quartier_id_from_iris)
            df = df.dropna(subset=['neighborhood_id'])
            
            # Mean of Medians
            agg = df.groupby('neighborhood_id')[target_col].mean().reset_index()
            agg.rename(columns={target_col: 'median_income'}, inplace=True)
            agg['year'] = year
            inc_results.append(agg)
            print(f"  Income {year}: Ready ({len(agg)} neighborhoods)")
        else:
            print(f"⚠️ Income {year}: No valid column found. Available: {df.columns[:5]}")

if inc_results:
    inc_final = pd.concat(inc_results, ignore_index=True)
else:
    inc_final = pd.DataFrame()

# %% [markdown]
# ## 5. Final Merge (Strict)

# %%
print("\n--- Merging ---")

# Start with Backbone
df_final = master_df.copy()

# Merge Real Estate
df_final = pd.merge(df_final, dvf_final, on=['neighborhood_id', 'year'], how='left')

# Merge Pop
if not pop_final.empty:
    df_final = pd.merge(df_final, pop_final, on=['neighborhood_id', 'year'], how='left')

# Merge Income
if not inc_final.empty:
    df_final = pd.merge(df_final, inc_final, on=['neighborhood_id', 'year'], how='left')

# Merge Geo Metadata
quartiers_meta = quartiers_gdf[['neighborhood_id', 'l_qu', 'area_km2', 'geometry']].rename(columns={'l_qu': 'neighborhood_name'})
df_final = pd.merge(df_final, quartiers_meta, on='neighborhood_id', how='left')

# Calculate Ratios
df_final['population_density'] = df_final['total_pop'] / df_final['area_km2']
df_final['pct_young_adults'] = (df_final['young_adults_pop'] / df_final['total_pop']) * 100
df_final['city'] = 'Paris'

# Reorder
cols = [
    'neighborhood_id', 'neighborhood_name', 'city', 'year',
    'median_income', 'median_price_per_m2',
    'population_density', 'pct_young_adults',
    'geometry'
]
df_final = df_final[cols]

# Report on "Wholeness"
print("\n--- Completeness Report ---")
for year in TARGET_YEARS:
    year_data = df_final[df_final['year'] == year]
    complete = year_data.dropna()
    print(f"Year {year}: {len(complete)} / 80 Neighborhoods are complete (Have Income + DVF + Pop).")

print("\n--- Sample ---")
print(df_final.head())

# Save
df_final.to_csv(OUTPUT_DIR / "paris_2015_2019_strict.csv", index=False)
print(f"\n✅ Saved strict dataset to {OUTPUT_DIR}")