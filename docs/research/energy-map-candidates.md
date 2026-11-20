# Energy-infrastructure maps as "in the wild" test material: candidates

*Compiled 2026-11-20.*

**Purpose.** Find real, static maps (raster or PDF) that have a legend and show energy infrastructure as **point symbols**. These are test inputs for the read-the-legend-then-find-every-symbol method, which so far has only been tested on OpenStreetMap renders.

**Categories.**
- **(a)** clean digital thematic maps
- **(b)** topographic sheets that include power symbols
- **(c)** scans of printed or historical maps

**How this was checked.** Each entry was checked against the publisher's or library's own page, an API (IIIF / STAC / Atom), or file headers. For most entries, a small crop of the legend and of the map body was also rendered and looked at. Pixel sizes come from IIIF manifests, STAC/GDAL or JP2 headers, unless the entry says otherwise. "(unverified)" marks anything that could not be checked against a primary source. The David Rumsey and NLS web pages, the Library of Congress, Stanford EarthWorks and the NRCan pages all served bot-challenge or 403 pages to automated requests. Where a page was blocked, the data came from IIIF/FTP endpoints instead, or the item is marked as unverified.

---

## 1. Summary table

| # | Map | Cat. | Country | Year | Format / size | Georef. | Energy point symbols | Licence | Ground truth |
|---|---|---|---|---|---|---|---|---|---|
| 1 | FPC *Principal Electric Facilities*, 8 regional sheets | c | US | 1971 (data to 30 Jun 1970) | IIIF JPEG, ~27,600 × 18,500 px per sheet | Graticule printed | Fuel plant ○ and hydro □ in 3 sizes, under construction, federal/non-federal flags, transmission/distribution substations △ | **Public Domain Mark** (7 sheets); one sheet is labelled CC BY-NC | Plant list printed on the sheet; EIA-860 (partial) |
| 2 | PG&E *Gas and electric transmission systems* | c | US (N. California) | 1939 | IIIF JPEG, 12,318 × 18,990 px | Georeferenceable (towns, coast) | Steam plant □, hydro plant ■, gas plant ○, substation o-, three "supplied" town dots | Rumsey: **CC BY-NC-SA 3.0** | None that matches the date; hand-labelling needed |
| 3 | Atlas of Canada 4th ed., *Electricity – Western Canada, Generating Stations 1968* | c | CA | 1972 (data 1968) | JPG 3030 × 2130 px at 150 dpi (1.9 MB); PDF 2.4 MB | Graticule printed | Hydro (black) and thermal (red) stations in 3 size classes, under-construction symbol | **OGL – Canada** | No 1968 point set; current datasets only partly match |
| 4 | Atlas of Canada 6th ed., *Generating Stations, 2007 – Power Source* | a | CA | 2009 (data 2007) | JP2 6879 × 6165 px (6.4 MB); ZIP with PDF and JPG (10.5 MB) | No (LCC projection stated) | 6 fuel colours × 4 capacity sizes (filled squares); 916 stations | **OGL – Canada** | GPPD / NACEI (later dates; partial) |
| 5 | UBA *Kraftwerke und Verbundnetze in Deutschland* | a | DE | 2026 | Vector PDF 2.4 MB (1584 × 2448 pt); PNG 1478 × 2328 | No | Proportional **pie charts** in 15 fuel colours; CHP outline | **Non-commercial only** ⚠ | UBA plant database and MaStR (same date) |
| 6 | DESNZ *Location of major UK electricity generation capacity since 1920* (decade maps) | a | UK | 2024 | PDF 2.1 MB; map images about 790–870 × 1100–1230 px | No | Same-size dots in 6 fuel colours (coal, gas, oil, hydro, wind, nuclear; plus others in later years) | **OGL v3.0** | DUKES 5.11 / REPD for 2023 maps; nothing for 1960 |
| 7 | EirGrid *Transmission System Map 2025* | a | IE / NI | 2025 | Vector PDF, A1, 3.5 MB | No | Stations at 400/275/220/110 kV, stations to be energised, plus thermal, wind, hydro, pumped storage, solar, wind/solar generation | **All rights reserved** ⚠ | OSM `power=substation/plant`; GPPD |
| 8 | ENTSO-E *Grid Map 2024 – Continental Europe* | a | EU | 2024 | Vector PDF 2.7 MB, 1:2.5M (5357 × 3288 pt) | No (schematic placement) | Substations, converters, phase shifters, plants by fuel type and capacity class | **© ENTSO-E, terms unclear** ⚠ | JRC-PPDB-OPEN, GPPD, OSM |
| 9 | Geobasis NRW *TK25 sheet 4418 Bad Wünnenberg* | b | DE | 2023 | PDF 8.6 MB (796 × 525 mm, legend on sheet); GeoTIFF tiles also offered | UTM and geographic ticks printed; GeoTIFF version available | Wind turbine, windmill, power station (Kraftwerk), substation, pylon line, chimney/cooling tower, transmitter mast | **dl-de/zero-2-0** | MaStR (current); ATKIS Basis-DLM (vector source) |
| 10 | swisstopo *National Map 1:25,000* (Swiss Map Raster 25) | b (c for old editions) | CH | 1984 → 2023 editions | COG GeoTIFF 14,000 × 9,600 px at 1.25 m (about 15 MB per sheet); legend supplied as separate PDF | **GeoTIFF** EPSG:2056 | Wind turbine, electrical substation, solar power, dam, power plant (2008 legend), HV line with pylons | **swisstopo OGD: free incl. commercial, attribution required** | swissTLM3D (vector source); OSM |
| 11 | Kadaster *TOP25raster* | b | NL | 2025 (plus 2023/2024) | GeoTIFF 8000 × 10,000 px at 1.25 m, 80 MB per sheet; legend PNG supplied with the WMS | **GeoTIFF** EPSG:28992 | Wind turbine, "windmotor", windmill, water-wheel mill, HV line with mast | **CC BY 4.0** | TOP10NL (vector source, CC BY 4.0); OSM |

Coverage: 3 × (c), 5 × (a), 3 × (b), across 7 countries plus one pan-European map. Entries 1, 3, 4, 6, 9, 10 and 11 are openly licensed.

---

## 2. Candidates

### 1. Federal Power Commission, *Principal Electric Facilities … Region* (8 sheets), 1971 — category (c)

- **Publisher / year:** United States Federal Power Commission, Bureau of Power. Printed by the U.S. Govt. Print. Off., Washington, 1971. "Based on information to June 30, 1970." Each sheet includes a key map, insets, a *Plant list* and an *Ownership list* (Stanford MODS record).
- **Landing pages (Stanford Libraries, Branner Map Collections):** Sheet 1 Northeastern [purl.stanford.edu/qw613fv3527](https://purl.stanford.edu/qw613fv3527) · Sheet 2 [bd995qv1262](https://purl.stanford.edu/bd995qv1262) · Sheet 3 [fb909df8176](https://purl.stanford.edu/fb909df8176) · Sheet 4 [tk834ms3316](https://purl.stanford.edu/tk834ms3316) · Sheet 5 [vz805vq4288](https://purl.stanford.edu/vz805vq4288) · Sheet 6 [cv410qy5184](https://purl.stanford.edu/cv410qy5184) · Sheet 7 [xx920zv5713](https://purl.stanford.edu/xx920zv5713) · Sheet 8 (AK/HI/PR/VI) [gd710gr0081](https://purl.stanford.edu/gd710gr0081). The regions are Northeastern, Great Lakes, North Central, Northwestern, Southwestern, South Central, Southeastern, and Alaska/Hawaii/Puerto Rico/Virgin Islands. Only Sheet 1 (Northeastern) and Sheet 8 (AK/HI/PR/VI) were matched to their regions, by title. The sheet-to-region order for the others was not confirmed.
- **Download:** IIIF Image API, e.g. `https://stacks.stanford.edu/image/iiif/qw613fv3527%2Fqw613fv3527_00_0001/full/full/0/default.jpg`. Use region requests such as `/x,y,w,h/1400,/0/default.jpg` to fetch tiles without downloading the full image.
- **Format / resolution:** JPEG via IIIF. Sheet 1 is 27,574 × 18,487 px. The other sheets are 27,127–32,413 px wide (manifest). Physical size is "110 × 132 cm or smaller", which works out to roughly 500–530 dpi (derived figure). Not georeferenced. A graticule and numbered marginal grid are printed, so the sheets can be georeferenced.
- **Legend (seen on Sheet 1):** *Generating stations*:
  - "Fuel" circles in 3 sizes (≥200,000 kW, 25,000–199,999 kW, ≤24,999 kW)
  - "Hydro" squares in the same 3 sizes. Each circle or square holds a number that refers to the plant list.
  - Publicly owned plants carry a flag: Federal (filled) or Non-Federal (open)
  - Under construction (dashed circle)
  - Substations: transmission △ and distribution △ (small)
  - *Transmission lines* in voltage classes (bonus line features)
- **Instance count:** Several hundred numbered plants plus many substations per regional sheet (estimate, from the length of the plant list on Sheet 1; not counted).
- **Licence:** Sheets 1, 2 and 4–8: *"This work has been identified as being free of known restrictions under copyright law, including all related and neighboring rights (Public Domain Mark 1.0)"*, and *"This item is in the public domain. There are no restrictions on use."* ⚠ **Sheet 3** (`fb909df8176`) is labelled *"Copyright © Stanford University. All Rights Reserved. … Creative Commons Attribution Non Commercial 3.0 Unported license (CC BY-NC)"*. A 1971 US federal work is public domain, so this label looks like a cataloguing inconsistency. Avoid sheet 3, or ask Stanford.
- **Ground truth:** The **printed plant list** on each sheet links symbol numbers to plant names and capacities. It is an internal ground truth for counts and classes; positions would need geocoding. EIA-860 has plant coordinates and operating years for plants still operating or recently retired. Many 1970 hydro and large thermal plants are in it, but plants retired before about 2000 are not, so EIA-860 covers only part of the map (date mismatch about 55 years).
- **Why useful / hard:** This is the closest historical analogue to a modern legend-driven map. It is monochrome, so classes differ only by **shape, size and an inner number**. The numbers make every instance unique-looking, and three sizes of the same shape are a good test of whether the method keeps size classes apart. Clutter is dense in the inset city maps. Scan quality is very good. Strong first (c) candidate.

### 2. *Gas and Electric Transmission Systems also Territory Served by the Pacific Gas and Electric Co.*, 1939 — category (c)

- **Publisher / year:** Pacific Gas and Electric Co. The date "1939" is printed under the scale bar (seen in the image). Library: David Rumsey Map Collection, image no. 52528 (seen on the sheet).
- **Landing page:** [davidrumsey.com … RUMSEY~8~1~289797~90061491](https://www.davidrumsey.com/luna/servlet/detail/RUMSEY~8~1~289797~90061491). The HTML page was blocked for automated requests; metadata came from the IIIF manifest `https://www.davidrumsey.com/luna/servlet/iiif/m/RUMSEY~8~1~289797~90061491/manifest`.
- **Download:** IIIF `https://www.davidrumsey.com/luna/servlet/iiif/RUMSEY~8~1~289797~90061491/full/full/0/default.jpg` (region requests work).
- **Format / resolution:** JPEG, 12,318 × 18,990 px. Physical size and DPI were not checked (unverified). Not georeferenced. It can be georeferenced from towns, county lines and the coastline; no graticule was seen.
- **Legend (seen):** Electric generating plants – steam (open □) and hydro (filled ■); gas generating plants (large ○); substation – electric (small o with a tick); "electricity supplied" (small ○), "gas supplied" (•) and "electricity & gas supplied" (⊙) at towns. Transmission lines are shown at 11, 17, 20, 22, 30/44, 60/70 and 110 kV, plus gas mains (bonus lines).
- **Instance count:** About 100+ plants and substations, plus several hundred supplied-town dots (estimate).
- **Licence:** The manifest gives no licence field. Per the Rumsey collection's published terms, the images are **CC BY-NC-SA 3.0**, and "commercial use" is defined as selling reproductions ([Stanford record for the Rumsey collection](https://purl.stanford.edu/xh235dd9059); [Rumsey About](https://www.davidrumsey.com/about); the wording was not re-read on the live page, which was blocked, so unverified). Research use with tiles sent to an API is probably acceptable, but **NC/SA** must be flagged if results are published.
- **Ground truth:** Nothing independent for 1939. Long-lived PG&E hydro plants (Pit, Feather and Mokelumne river plants) can be matched to EIA-860 and the Global Power Plant Database (GPPD), but only partially. Plan on hand-labelling.
- **Why useful / hard:** This is a hard case. The symbols are **tiny, sepia, on toned paper**. Three of the seven point classes are small circle variants that differ only by fill (○ / • / ⊙), and they are easy to confuse with ordinary town dots and lettering. It is a good stress test for symbol discrimination and false positives.

### 3. Atlas of Canada, 4th ed., *Electricity – Western Canada: Generating Stations, 1968* — category (c)

- **Publisher / year:** Department of Energy, Mines and Resources Canada, *National Atlas of Canada*, 4th ed. (1974). Published 1972-01-14; shows 1968 conditions. Pages 235–236.
- **Landing page:** [open.canada.ca dataset 3b3f2406…](https://open.canada.ca/data/en/dataset/3b3f2406-3aba-5efa-a86b-1162a7acaa56)
- **Download:** [235_236.jpg](https://ftp.geogratis.gc.ca/pub/nrcan_rncan/raster/atlas_4_ed/eng/economic/resourceindustries/235_236.jpg) (1,909,046 B) · [235_236.pdf](https://ftp.geogratis.gc.ca/pub/nrcan_rncan/raster/atlas_4_ed/eng/economic/resourceindustries/235_236.pdf) (2,422,929 B).
- **Format / resolution:** JPG 3030 × 2130 px at 150 dpi (from the file header). This is low resolution for a two-page atlas spread. Not georeferenced. A graticule and the projection (Lambert Conformal Conic, standard parallels 49°N and 77°N) are printed.
- **Legend (seen):** Existing stations by installed capacity (1,500–9,999 kW; 10,000–99,999 kW; 100,000–999,999 kW), shown in two styles: hydro-electric (black) and thermal-conventional (red). There is an "under construction or in advanced planning" symbol. The map also has proportional circles for total capacity per river or thermal station (black for rivers, red for thermal), and coloured service-area polygons for utilities.
- **Instance count:** About 150 station dots plus about 60 proportional circles (estimate, from the overview).
- **Licence:** **Open Government Licence – Canada** ([OGL-C](https://open.canada.ca/en/open-government-licence-canada)), as listed on the dataset record.
- **Ground truth:** No 1968 point dataset. Many hydro stations still operate and can be matched to GPPD or to NRCan/NACEI "Power Plants, 100 MW or more" ([open.canada.ca](https://open.canada.ca/data/en/dataset/40fbe40c-01cd-49d3-8add-0d20ed64c90d)), but only partly. Mostly hand-labelling.
- **Why useful / hard:** Tiny dots, about 3–6 px at 150 dpi, sit **inside large proportional circles and on coloured area fills**. Colour (black vs red) carries the class. It is a good low-resolution, high-clutter case. Siblings in the same series: *Electricity – Eastern Canada Generating Stations, 1968* ([record](https://donnees.iriu.ca/dataset/02096709-bda3-5cc0-8207-6f06dc78aec4), not opened) and the 3rd-ed. (1957) *Hydro and Fuel Electric Power – Western Canada* (not opened).

### 4. Atlas of Canada, 6th ed. (archival), *Generating Stations, 2007 – Power Source* (map 6184) — category (a)

- **Publisher / year:** Natural Resources Canada, © 2009. Source: Statistics Canada, *Electric Power Generating Stations, 2007* (printed on the map).
- **Landing page:** FTP directory [atlas_6_ed/eng/](https://ftp.geogratis.gc.ca/pub/nrcan_rncan/raster/atlas_6_ed/eng/). The companion by-fuel 1997 map has a record at [open.canada.ca cd7e956e…](https://open.canada.ca/data/en/dataset/cd7e956e-8893-11e0-a92d-6cf049291510); a separate record for the 2007 map was not located (unverified).
- **Download:** [6184_generating_stations_2007_by_power_source.jp2](https://ftp.geogratis.gc.ca/pub/nrcan_rncan/raster/atlas_6_ed/eng/6184_generating_stations_2007_by_power_source.jp2) (6,384,542 B) · `.zip` with PDF and JPG (10,526,787 B).
- **Format / resolution:** JP2, 6879 × 6165 px, lossy (gdalinfo). Not georeferenced; no geo boxes in the JP2. The projection is stated (LCC, standard parallels 49°N and 77°N). No graticule was seen, so georeferencing would rely on place-name control points.
- **Legend (seen):** Generating stations by power source, shown as coloured filled squares: coal (magenta), natural gas (olive), petroleum (brown), biomass (yellow), nuclear (purple; the map spells it "unranium"), and flow renewables – wind, tide, water (teal). Capacity is shown by square size in 4 classes (500–9,999 kW … 1,000,000–5,616,000 kW). Map text: *"The map shows the 916 generating stations … 479 hydroelectric stations, 375 thermal plants …, 7 nuclear plants, 54 wind turbines and 1 tidal power plant."*
- **Instance count:** **916** (stated on the map).
- **Licence:** **OGL – Canada** (stated for the 6th-edition atlas records on open.canada.ca; the 2007 map's own record was not found, so this is inferred for this exact file).
- **Ground truth:** Statistics Canada's 2007 station list is not known to be public with coordinates (unverified). GPPD (2018–2021) and NACEI power plants ≥100 MW (later years) match only partly, because of the date difference and the 500 kW map threshold.
- **Why useful / hard:** A clean digital map. Symbol shape is constant, so **colour × size** is the whole signal. Squares share map space with population-place symbols (open squares and circles), which tests confusion with non-energy legend items. A large instance count with a stated total gives a free recall check. Moderate difficulty. Siblings in the same directory: 1997 maps by capacity, fuel and operator (6173–6175, 6879 × 6163 px).

### 5. Umweltbundesamt, *Kraftwerke und Verbundnetze in Deutschland*, 2026 — category (a)

- **Publisher / year:** Umweltbundesamt (UBA), © 2026. The imprint reads "Kraftwerke in Betrieb, Stand August 2026; Deutsches Höchstspannungsnetz, Stand August 2026" (seen on the PNG). The landing page text said "Stand Juni 2026", so the two sources disagree slightly.
- **Landing page:** [umweltbundesamt.de/bild/kraftwerke-verbundnetze-in-deutschland](https://www.umweltbundesamt.de/bild/kraftwerke-verbundnetze-in-deutschland)
- **Download:** [DE_Kraftwerkskarte_2026_0.pdf](https://www.umweltbundesamt.de/system/files/medien/372/bilder/dateien/DE_Kraftwerkskarte_2026_0.pdf) (2,428,338 B) · PNG `https://www.umweltbundesamt.de/system/files/image/DE_Kraftwerkskarte_2026_0.png` (1478 × 2328 px).
- **Format / resolution:** Vector PDF (Adobe Illustrator, 1584 × 2448 pt; only one small raster image embedded), so it can be rendered at any DPI. Not georeferenced; no graticule.
- **Legend (seen):** "Kraftwerke ab 100 MWel" are drawn as **proportional pie charts** (350–4000 MW) split by fuel: Braunkohle, Steinkohle, Erdgas, Heizöl, Ölrückstand, Konvertergas, Abfall, Raffineriegas, Gichtgas, Wind (offshore parks), Wasser, Biomasse, Photovoltaik, Batteriespeicher. A black outline marks CHP. Lines: sea cables and 380 / 220 / 155 kV, planned ≥380 kV. Area fills show the four TSO zones.
- **Instance count:** About 250 pies (estimate). Many sit in labelled leader-line callouts.
- **Licence:** ⚠ **Non-commercial only.** UBA: the map *"dem Urheberrecht unterliegt und nur zur nichtkommerziellen Nutzung verwendet werden darf"*. Sending tiles to an API for research is arguably non-commercial, but publishing figures needs care or permission.
- **Ground truth:** UBA's database *"Kraftwerke in Deutschland"* (same source, updated twice a year with the map; [UBA page](https://www.umweltbundesamt.de/themen/klima-energie/energieversorgung/strom-waermeversorgung-in-zahlen)). It is also non-commercial, and whether it has coordinates is unverified. The **Marktstammdatenregister** has unit coordinates (dl-de/by-2-0, unverified here) and matches the date.
- **Why useful / hard:** An adversarial case for a glyph detector. One "symbol" is a **multi-class pie of variable size**, so the legend gives colour swatches, not glyph templates. Pies overlap heavily in the Rhine–Ruhr area. It tests whether the method can fall back to colour-swatch matching inside a container shape. Siblings (same licence): *Kraftwerke und Windleistung*, *Kraftwerke und Photovoltaikleistung*, *KWK-Karte*.

### 6. DESNZ, *Location of major UK electricity generation capacity since 1920* (Energy Trends, March 2024) — category (a)

- **Publisher / year:** Department for Energy Security and Net Zero, 28 Mar 2024.
- **Landing page:** [gov.uk publication](https://www.gov.uk/government/publications/energy-trends-march-2024-special-feature-article-location-of-major-uk-electricity-generation-capacity-since-1920)
- **Download:** [PDF](https://assets.publishing.service.gov.uk/media/660445a1f9ab41001aeea416/Location_of_major_UK_electricity_generation_capacity_since_1920.pdf) (2,141,765 B, 10 pages) · [data tables xlsx](https://assets.publishing.service.gov.uk/media/660445b291a320001182b115/UK_Electricity_capacity_per_region_1940-2023.xlsx) (39,711 B).
- **Format / resolution:** Each map is an embedded JPEG, about 790–870 × 1100–1230 px at 220 ppi. The page-3 1960 map, for example, is 861 × 1217 px. Extract the images with `pdfimages -j`; there are about 15 maps (charts 2–3 plus the appendix). Not georeferenced; a UK outline with region boundaries only.
- **Legend (seen, 1960 map):** "Sites in 1960": Coal, Gas, Oil, Hydro, Wind, Nuclear. All are **identical filled dots differing only in colour**. Later decades add more fuel classes (seen in the text; not every map was opened).
- **Instance count:** About 200 dots on the 1960 map (estimate); more on the 2023 map.
- **Licence:** **OGL v3.0**. From the PDF: *"This publication is licensed under the terms of the Open Government Licence v3.0 except where otherwise stated."*
- **Ground truth:** The xlsx holds only **regional totals**, not site points. For the 2023 map, use DUKES Table 5.11 (power stations in the UK; whether it has coordinates is unverified) and REPD for renewables. No point ground truth for 1960–2000.
- **Why useful / hard:** The easiest case and a good **sanity baseline**. One glyph shape, so success depends only on colour. Dots overlap in London and the Midlands. The same legend is redrawn across decades, which allows a temporal series.

### 7. EirGrid, *Transmission System Map – 400, 275, 220 & 110 kV Transmission System 2025* — category (a)

- **Publisher / year:** EirGrid Group. PDF created 17 Feb 2025 (Esri ArcGIS Pro 3.2).
- **Download (also the landing):** [EirGrid_Transmission_System_Map_TOP25_FINAL_20250217.pdf](https://www.eirgrid.ie/sites/default/files/publications/EirGrid_Transmission_System_Map_TOP25_FINAL_20250217.pdf) (3,461,945 B).
- **Format / resolution:** Vector PDF, A1 (1684 × 2384 pt). Not georeferenced. Insets for Belfast, Cork and Dublin.
- **Legend (seen):** 400 / 275 / 220 / 110 kV station (small coloured squares or crosses); station to be energised in 2025. *Transmission-connected generation*: Thermal, Wind, Hydro, Pumped Storage (▼), Solar, Wind/Solar. Lines: 400/275/220/110 kV overhead, 220/110 kV underground cable, HVDC cable.
- **Instance count:** Several hundred stations and about 100+ generators (estimate).
- **Licence:** ⚠ **Restrictive.** The EirGrid legal page says materials may not be *"copied, modified, reproduced, republished, or distributed for public or commercial purposes"* without prior written permission, and any permitted reuse must keep the content *"intact"*.
- **Ground truth:** OSM `power=substation` / `power=plant` for Ireland (current, good date match); GPPD (2021). EirGrid does not publish a station register with coordinates (unverified).
- **Why useful / hard:** The station symbols are very small and differ by colour at almost the same shape, so they test **fine colour discrimination**. Generator symbols sit next to station symbols and labels. Use for internal testing only, unless permission is obtained.

### 8. ENTSO-E, *Grid Map 2024 – Interconnected network of Continental Europe* (1:2,500,000) — category (a)

- **Publisher / year:** ENTSO-E, "© ENTSO-E 2024". Download page updated 20 Nov 2024.
- **Landing page:** [entsoe.eu/data/map/downloads](https://www.entsoe.eu/data/map/downloads/)
- **Download:** [ENTSOE_Grid_Map_Continental_Europe.pdf](https://www.entsoe.eu/Documents/Publications/maps/2024//ENTSOE_Grid_Map_Continental_Europe.pdf) (2,741,269 B). Also available: the whole ENTSO-E area at 1:4M, Northern Europe at 1:3M, and 2023 and 2019 editions.
- **Format / resolution:** Vector PDF, 5357 × 3288 pt (about 189 × 116 cm), ArcGIS Pro. Not georeferenced. ENTSO-E states that network elements are **not at their exact geographic location**.
- **Legend (from the PDF text layer):** Substation; substation under construction; converter station; back-to-back converter; phase shifter. Power plants by type: nuclear, hydro (run-of-river & pondage, pure storage, pure pump storage, mixed pump storage, marine), solar PV, solar thermal, wind farm, biomass, geothermal, and thermal by main fuel, with capacity classes ("NGC equal or higher than…" thresholds).
- **Instance count:** Thousands (estimate).
- **Licence:** ⚠ The map carries only "© ENTSO-E 2024". The download page links to a Disclaimer, but no reuse terms were found. **Unclear; treat as restrictive.**
- **Ground truth:** JRC Open Power Plants Database (JRC-PPDB-OPEN, CC BY 4.0; date about 2019, unverified), GPPD, OSM. The schematic placement means scoring must allow large positional tolerance or work on topology only.
- **Why useful / hard:** The richest energy legend in this list (about 20 point classes) and very dense. It tests whether legend parsing scales up. Not good for position scoring.

### 9. Geobasis NRW, *Topographische Karte 1:25 000, sheet 4418 Bad Wünnenberg* (2023) — category (b)

- **Publisher / year:** Land Nordrhein-Westfalen / Bezirksregierung Köln, Geobasis NRW; "Ausgabe 2023" (metadata: 2023-12).
- **Landing page:** [OpenGeodata.NRW TK25 PDF index](https://www.opengeodata.nrw.de/produkte/geobasis/tk/akt/tk25/tk25_s_pdf/). Georeferenced GeoTIFF tiles are in the sibling folder `dtk25_farbe_tiff/`.
- **Download:** `https://www.opengeodata.nrw.de/produkte/geobasis/tk/akt/tk25/tk25_s_pdf/4418_Bad_W%C3%BCnnenberg.pdf` (8,641,021 B). There are 272 standard sheets of about 8–10 MB each.
- **Format / resolution:** Single-page PDF, 796 × 525 mm, with the legend, publisher block and licence **on the sheet**. GDAL renders it at 15,920 × 10,500 px by default. The PDF has no embedded georeferencing. The CSV metadata gives EPSG 25832, and UTM 32U kilometre ticks plus geographic ticks are printed, so it is georeferenceable. The GeoTIFF product is georeferenced.
- **Legend (seen, "Ver- und Entsorgung"):** Kraftwerk (lightning bolt in a box); Hochspannungsleitung mit Mast und Umspannwerk (HV line with pylon and substation); Windmühle / **Windkraftanlage**; Schornstein / Kühlturm; Sendeturm / Sendemast; Erdöl-/Erdgasförderanlage; Bergbau; Förderband / Rohrleitung.
- **Instance count:** About 100+ wind turbine symbols on this sheet, plus 2 power-station or substation symbols and pylons along the HV lines (estimate from the overview and crops). This area (Sintfeld, Paderborn district) is one of Germany's densest onshore wind areas.
- **Licence:** **Datenlizenz Deutschland – Zero – 2.0**. Imprint: *"Veröffentlicht unter der Datenlizenz Deutschland - Zero - Version 2.0 (http://www.govdata.de/dl-de/zero-2-0)"* (read on the sheet; also listed on the open.nrw catalogue).
- **Ground truth:** **Marktstammdatenregister** (MaStR) wind units with coordinates (dl-de/by-2-0, unverified); matches the date, but the 2023 map lags the register. **ATKIS Basis-DLM** (the vector source of the DTK; open in NRW, unverified) is the exact source. OSM `power=generator` + `generator:source=wind`.
- **Why useful / hard:** The best (b) candidate. The legend is on the same sheet, the licence is fully open, ground truth is strong, and there are many instances. Turbine glyphs are small black three-bladed symbols that look similar to the windmill and mast glyphs next to them in the legend, which is a real discrimination test. Other suggested sheets: **4905 Grevenbroich, 5005 Bergheim and 5006 Frechen** (lignite plants Neurath, Niederaußem and Frimmersdorf, substations, pylons); **4319 Lichtenau** (wind).

### 10. swisstopo, *National Map 1:25,000* (Swiss Map Raster 25), e.g. sheet 1125 Chasseral, 2023 — category (b); older editions approach (c)

- **Publisher / year:** Federal Office of Topography swisstopo. 247 sheets, revised on a 6-year cycle. The STAC collection covers editions from **1984 to 2023**.
- **Landing page:** [STAC collection ch.swisstopo.pixelkarte-farbe-pk25.noscale](https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.pixelkarte-farbe-pk25.noscale) · [product page](https://www.swisstopo.admin.ch/en/national-map-1-25000)
- **Download:** e.g. `https://data.geo.admin.ch/ch.swisstopo.pixelkarte-farbe-pk25.noscale/swiss-map-raster25_2023_1125/swiss-map-raster25_2023_1125_komb_1.25_2056.tif` (14,683,235 B). The 2018, 2020 and 2021 editions of sheet 1125 are also listed. Legend: [Conventional signs 2024 (EN PDF)](https://api3.geo.admin.ch/static/images/legends/ch.swisstopo.landeskarte-farbe-10_en_big.pdf) and the [2008 legend](https://www.swisstopo.admin.ch/dam/en/sd-web/WxsMJ4yE7xeV/Zeichenerklaerung_2008_e.pdf).
- **Format / resolution:** Cloud-optimised **GeoTIFF**, 14,000 × 9,600 px at 1.25 m/px, EPSG:2056, with overviews. Windows can be read over HTTP with `gdal_translate /vsicurl/…`, so no full download is needed. The legend is **supplied separately**, not on the raster.
- **Legend (from the 2024 and 2008 legend PDFs):** Wind turbine; electrical substation; solar power; dam / dam wall; "power plant with switching station" (2008); high-tension transmission line with pylons; cooling tower.
- **Instance count:** Sparse. Sheet 1125 shows a few Mont-Crosin wind-turbine glyphs near its western edge; most of the wind park is on the neighbouring sheet 1124 (seen in crops). Alpine sheets have more dams, substations and plants.
- **Licence:** swisstopo free geodata: *"A reference to the source is mandatory"* (e.g. "© swisstopo"). The data *"may be enriched and processed and also used commercially"* ([terms](https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-and-geoservices)). The STAC metadata field says "proprietary" but links to these OGD conditions.
- **Ground truth:** **swissTLM3D** (the vector source of the national map; free under the same OGD terms, unverified). The SFOE wind-turbine dataset on opendata.swiss (unverified). OSM.
- **Why useful / hard:** The cartography is very fine: small black glyphs among dense hachures, rock drawing and tree dots, so false positives are likely. Having editions from 1984 to 2023 for the same sheet gives a **temporal series** (turbines appear after the 1990s) and older scan-derived editions. The legend is a separate file, which tests the "legend supplied with it" path.

### 11. Kadaster, *TOP25raster* (Basisregistratie Topografie), e.g. sheet 15h (Noordoostpolder), 2025 — category (b)

- **Publisher / year:** Kadaster. Derived automatically from TOP10NL; 2025 edition (2023 and 2024 nationwide archives also in the feed).
- **Landing page:** [PDOK Atom feed](https://service.pdok.nl/brt/topraster/atom/top25raster.xml) · [data.overheid.nl record](https://data.overheid.nl/dataset/10968-top25raster)
- **Download:** Per sheet, e.g. `https://service.pdok.nl/kadaster/brt-topraster/atom/downloads/15h-top25raster-2025.tif` (80,062,278 B each; 390 sheets). Nationwide zip is about 4.5 GB. Sheet index: `kaartbladindex_top25raster.json`. Legend: [top25raster legend PNG](https://service.pdok.nl/brt/topraster/wms/v1_0/legend/top25raster/default.png) (300 × 2250 px).
- **Format / resolution:** **GeoTIFF**, 8000 × 10,000 px at 1.25 m/px, EPSG:28992, paletted, strip-organised. Windows can be read with `/vsicurl/`; a 2.5 km window was extracted without downloading the whole file. The legend is supplied separately, not on the sheet.
- **Legend (seen):** Under "Overige symbolen": windmolen, waterradmolen, **windmotor**, **windturbine**; hoogspanningsleiding met mast (HV line with mast); oliepompinstallatie; seinmast / zendmast; gemaal (pumping station).
- **Instance count:** A 2.5 × 2.5 km window of sheet 15h showed 5 wind turbines. Sheets covering the large Noordoostpolder and Flevoland wind parks should hold dozens (estimate).
- **Licence:** **CC BY 4.0** (`<rights>https://creativecommons.org/licenses/by/4.0/deed.nl</rights>` in the Atom feed).
- **Ground truth:** **TOP10NL** (the vector source of this raster; CC BY 4.0 per PDOK, unverified), which gives exact-source ground truth. A national wind-turbine dataset is on data.overheid.nl (licence unverified). OSM.
- **Why useful / hard:** The rendering is very clean. Turbine glyphs are **drawn at arbitrary rotations** (seen: the three-blade symbol is rotated per instance), which a template matcher that ignores rotation will miss. The windmolen / windmotor / windturbine classes are near-duplicates. It also has an exact vector ground truth with matching date.

---

## 3. Also looked at, not included

- **NLS, OS Ten-Mile Planning Map Sheet 1, *Great Britain: electricity, statutory supply areas*, 1946** ([maps.nls.uk/view/230555892](https://maps.nls.uk/view/230555892)). CC BY per the search snippet. The title points to area polygons rather than point symbols. The NLS page could not be opened (bot challenge), so it is unverified whether the map marks generating stations.
- **Geoscience Australia, National Electricity Infrastructure** (CC BY 4.0). Only vector data and map services were found, no static published map with a legend. A render would just be another self-made render, like the OSM case.
- **David Rumsey utility maps** with IIIF access confirmed: *The Detroit Edison system* (7371 × 9274 px), *The Cleveland Electric Illuminating Company* (14,080 × 9,239 px), *Properties of Central States Electric Company* (7361 × 9235 px), and two Soviet electrification maps (5898 × 4240 and 8867 × 5011 px). These are possible extra (c) items under the same CC BY-NC-SA terms; their legends were not inspected.
- **Library of Congress** holdings of the FPC series (1935 National Power Survey, 1949, 1962, 1977 national editions) are listed in other library catalogues. loc.gov returned 403 to automated requests, so they are unverified.

---

## 4. Recommended first 3–5 to try, and why

1. **NRW TK25 4418 Bad Wünnenberg (#9).** Legend on the sheet, fully open licence (dl-de/zero), about 100 instances of one dominant class (wind turbine), visually similar distractor classes, and MaStR / ATKIS ground truth that roughly matches the date. Closest to the OSM setting but with real cartography. Best first test.
2. **Kadaster TOP25raster (#11).** Open (CC BY 4.0), georeferenced, exact vector ground truth (TOP10NL). **Rotated turbine glyphs** and near-duplicate mill classes isolate one specific weakness. Legend supplied separately.
3. **Atlas of Canada 2007 by power source (#4).** Clean digital thematic map, open licence, 916 stated instances, and classes encoded as colour × size, which differs from the topo glyph case. The stated total gives an immediate recall check, even before point-level ground truth is set up.
4. **FPC Principal Electric Facilities, Northeastern sheet, 1970 (#1).** The best historical scan. Public domain, very high resolution, a clear legend with shape and size classes, and a printed plant list as internal ground truth. Avoid sheet 3, which has the inconsistent licence label.
5. **Stretch / adversarial:** *DESNZ UK 1960* (#6) as a trivial colour-only baseline, then **PG&E 1939** (#2) or **Atlas of Canada 1968** (#3) for low-contrast, low-resolution scans. Use the UBA (#5), EirGrid (#7) and ENTSO-E (#8) maps only internally unless permission is obtained, because their licences are non-commercial or all-rights-reserved.
