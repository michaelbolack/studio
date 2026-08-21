# Florida county geometry

\`florida-counties.geojson\` is a Florida-only extract of Plotly's public
\`geojson-counties-fips.json\` dataset. Each feature is keyed by its five-digit
U.S. Census county FIPS code. The extraction recipe is documented at
<https://github.com/danielcs88/fl_geo_json>.

For geographic authority and future boundary refreshes, use the U.S. Census
Bureau TIGERweb Counties layer:
<https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1>.

Run \`python3 scripts/validate_florida_heatmap.py\` after replacing this file.
The validator fails unless all 67 Florida county names and FIPS identifiers
match the fixed inventory and every feature contains nonempty polygon geometry.
