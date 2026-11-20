# Automatic map digitization with AI/ML: literature review

*Compiled 2026-11-19. Covers work published on or after 2021-11-19.*

**Scope.** This review covers digitizing **scanned or rendered cartographic documents**: topographic sheets, historical city and atlas maps, cadastral plans, insurance maps, and geologic, land-use and other thematic maps. Work whose main input is satellite, aerial or drone imagery is **excluded**. That includes building, road and land-cover extraction from imagery. A paper that uses imagery only as a side signal stays in if its main input is a map, and the entry says so. No paper below depends on imagery.

**How to read this.** Every factual claim has a link to the paper, the publisher's DOI, an official dataset page or an official repository. "(unverified)" means the detail could not be checked against a primary source, usually because the full text was paywalled or blocked during this review. Numbers are copied from the papers. They are rarely comparable across papers, because each paper uses different data and metrics.

---

## 1. Executive summary

- **Text (OCR / text spotting) is the most mature area and has the best shared benchmarks.** The ICDAR 2024 and 2025 MapText competitions released public, polygon-annotated datasets (David Rumsey maps, French land registers, Taiwanese topographic maps) along with evaluation code. The best systems are fine-tuned scene-text spotters built on DETR-style transformers, such as DeepSolo/DNTextSpotter and TESTR/PALETTE. Word detection now reaches about 90% harmonic mean on Rumsey maps. Recognition, and especially linking words into multi-word place names, is still much harder ([MapText 2024](https://doi.org/10.1007/978-3-031-70552-6_22), [MapText 2025](https://doi.org/10.1007/978-3-032-04630-7_33)).
- **Point and glyph detection is the thinnest area.** Most papers use off-the-shelf detectors (Mask R-CNN, YOLO variants) on one map series with a few symbol classes. They output bounding boxes, and the box centre is used as the point location. Two ideas stand out. YOLSO predicts symbol *centres* directly on fixed-size symbols and scored 97.9% point mAP@0.5 on Ordnance Survey tree symbols ([Smith & Pillatt 2023](https://doi.org/10.1007/978-3-031-41734-4_14)). Legend-prompted ("one-shot") detection uses the map's own legend symbol as the query ([Saxton et al. 2024](https://doi.org/10.3390/geosciences14110305)). A first generic, cross-collection sign benchmark (CaSiDD) appeared in Oct 2026 as a preprint ([Petitpierre 2026](https://arxiv.org/abs/2610.13224)).
- **Area and line extraction is dominated by U-Net-style semantic segmentation.** It is trained on a few hand-labelled sheets of one series, mostly Swiss Siegfried, USGS topographic or Ordnance Survey maps. Recent work cuts labelling cost with synthetic "imitation maps", contrastive pre-training across map editions, weak labels from neighbouring editions, and fine-tuned foundation models such as MapSAM.
- **Geologic maps (the DARPA/USGS AI for Critical Mineral Assessment Competition, AI4CMA) pushed legend-driven extraction.** The task is "given the legend swatch, find every matching polygon, fault line or point symbol". DIGMAPPER is the most complete published system. It uses LayoutLMv3 plus GPT-4o for the legend, a transformer for polygons, a graph model for lines and YOLOv8 for points, plus georeferencing ([Duan et al. 2025](https://arxiv.org/abs/2506.16006)).
- **Georeferencing is mostly solved with text plus a gazetteer, or with feature matching against already-georeferenced maps.** Examples are OCR + geocoding ([Milleville et al. 2022](https://doi.org/10.3390/ijgi11070387)), OCR of corner coordinates + multimodal LLM ([Tyagi & Dubey 2026](https://doi.org/10.1007/978-3-032-08511-5_8)), and SuperPoint/SuperGlue matching to "anchor" maps ([Vaienti et al. 2025](https://doi.org/10.1080/15230406.2025.2566789)).
- **End-to-end vectorization (closed shapes into clean polygons) is still hard.** The best result on the Paris atlas benchmark is about 51% panoptic quality ([Chen et al. 2024](https://doi.org/10.1371/journal.pone.0298217)).

**This review contains 35 papers.**

---

## 2. Summary table

Task codes: **PT** = point/glyph detection, **AR** = area/polygon extraction, **LN** = line extraction, **TX** = OCR/text spotting/linking, **GR** = georeferencing, **E2E** = end-to-end or vectorization system.

| # | Paper (first author, year) | Task | Training data | Eval data | Code/data public? |
|---|---|---|---|---|---|
| P1 | Vassányi & Gede 2021, point symbols on archive maps | PT | Third Military Survey (Austro-Hungarian) sheets, 4 symbol classes | Held-out complete sheet | (unverified) |
| P2 | Huang et al. 2023, ASPP-YOLOv4 point symbols | PT | 1,909 scanned + 2,505 vector-rendered Chinese large-scale topo map images | Same sources (held out); mAP, IoU | (unverified) |
| P3 | Smith & Pillatt 2023, YOLSO | PT (+AR) | 135 OS 1:2500 1st-edition tiles, Yorkshire; 22,882 tree points, 782 woodland polygons | Held-out tiles; point mAP@0.5 | Stated public (URL unverified) |
| P4 | Saxton et al. 2024, open-set geologic extraction | PT + AR | AI4CMA geologic maps (USGS/DARPA) | AI4CMA maps; median F1 | (unverified) |
| P5 | Pai et al. 2025, tea symbols Taiwan | PT | Early-20th-c. Taiwanese maps (1900s, 1920s), land-use symbols | (unverified) | (unverified) |
| P6 | Petitpierre 2026, CaSiDD sign detection | PT | CaSiDD: 796 patches, 18,750 sign labels | CaSiDD; precision/recall at IoU 0.3/0.5 | Dataset yes (Zenodo) |
| A1 | Lin F. et al. 2023, polygon metadata | AR | USGS geologic maps + legend ("map key") | USGS geologic maps; median F1 | (unverified) |
| A2 | Wu et al. 2022, hydrology + uncertainty | AR/LN | Scanned historical topo maps (series unverified) | Dice | (unverified) |
| A3 | Wu et al. 2023, domain adaptation via co-occurrence | AR | Swiss Siegfried + old national maps | Cross-series segmentation | Yes (GitHub) |
| A4 | Ståhl & Weimann 2022, wetlands | AR | Generalstabskartan (Sweden), Jönköping county, hand-labelled | 10-fold CV; F1 | GIS layer released |
| A5 | Lin Y. et al. 2023, Sanborn 3D | AR (+TX) | 13 Sanborn sheets (Columbus, OH, 1961) | Pixel/object F1 | Yes (figshare) |
| A6 | Xia et al. 2025, MapSAM | AR/LN | Siegfried: railway (5,872 tiles) and vineyard (613 tiles) | IoU, F1, few-shot | Yes (announced) |
| A7 | Yuan et al. 2025, age-tracing | AR | "Hameln" dataset, 1897–2017 German topo maps 1:25k | mIoU, OA | (unverified) |
| A8 | Yuan & Sester 2025, LLM-distilled labels | AR | Historical maps, LLM coarse labels (no fine manual labels) | IoU/precision, Wood/Settlement | (unverified) |
| A9 | Rabehi et al. 2025, French urban footprints | AR | IGN "Scan Histo" (1925–1950) | 941 tiles, metropolitan France; OA 73% | Stated released (links unverified) |
| A10 | Hosseini et al. 2022, MapReader | AR (patch) | ~16K OS 19th-c. sheets; 62,020 labelled patches | 12,404 test patches; F1 | Yes (GitHub, JOSS) |
| L1 | Uhl et al. 2022, past road networks | LN | USGS historical topo maps, 42 sheets (1890–1950) + modern roads | Manual reference; F1 | (unverified) |
| L2 | Jiao et al. 2022, symbol reconstruction | LN | Siegfried map; real + synthetic "imitation maps" | Siegfried test areas | (unverified) |
| L3 | Jiao et al. 2024, road vectorization + classes | LN | Siegfried map | (unverified) | (unverified) |
| L4 | Xia et al. 2023, contrastive railway | LN | Siegfried + Old National Map pairs (self-supervised) | Railway segmentation | (unverified) |
| L5 | Mühlematter et al. 2024, probabilistic road classes | LN | Synthetic re-painted Siegfried roads | 2 Siegfried sheets; completeness/correctness | (unverified) |
| L6 | Kramm et al. 2025, Kenya roads | LN | 533 Kenyan topo maps 1:50k/1:100k (1950s–80s), 20 road symbols | 7 sheets; F1 0.84 | Data + scripts (CC BY 4.0) |
| T1 | Li Z. et al. 2024, ICDAR MapText 2024 | TX | Rumsey (200 train tiles) + French land registers | Rumsey 700 test tiles, French; PDQ/PWQ/PCQ | Yes (Zenodo, GitHub) |
| T2 | Lin Y. et al. 2025, ICDAR MapText 2025 | TX | + more French tiles, Taiwanese maps, synthetic sets | 3 datasets; H-mean of P/R/T/C/link P/R | Yes (Zenodo, GitHub) |
| T3 | Lin & Chiang 2024, PALETTE + SynthMap+ | TX | SynthMap+ (73,657 synthetic images) + scene text | Rumsey-309, Grinnell-UMass-31; E2E F1 | Yes |
| T4 | Kim et al. 2023, mapKurator | TX/E2E | Synthetic maps + scene text + human labels | Deployment on 60K+ Rumsey maps | Yes |
| T5 | Lin Y. et al. 2025, LIGHT linking | TX | MapText Rumsey + 397,385 auto-labelled Rumsey tiles | MapText Rumsey test; link F1 | Yes |
| T6 | Olson et al. 2024, multiword search | TX | (no training; MST heuristic) | MapText 2024 data; link P/R | (unverified) |
| T7 | Zou et al. 2025, attentive pointer sequencing | TX | (unverified) | 1890s OS London (285,846 sequences) | Preprint CC BY |
| G1 | Milleville et al. 2022, OCR georeferencing | GR | Pretrained OCR + public geocoders | 16 historical + 9 modern topo maps | (unverified) |
| G2 | Vaienti et al. 2025, feature matching + Delaunay | GR | Georeferenced "anchor" maps (SuperPoint/SuperGlue) | (unverified) | (unverified) |
| G3 | Tyagi & Dubey 2026, OCR + multimodal LLM | GR | EasyOCR + MLLM (no training reported) | 12 topo sheets; RMSE | (unverified) |
| E1 | Chen Y. et al. 2024, vectorization benchmark | E2E/AR | Paris Atlas Municipal 1926 sheet; 8,362 polygons | 1898 sheet; COCO PQ | Yes (GitHub, Zenodo CC BY 4.0) |
| E2 | Duan et al. 2025, DIGMAPPER | E2E (PT/LN/AR/GR) | AI4CMA maps + ~10K synthetic point patches | 100+ AI4CMA maps; F1, RMSE | Partly (CriticalMAAS repos) |
| E3 | Kirsanova et al. 2025, GPT-4o legend detection | E2E (legend) | In-context examples (no training) | USGS maps; F1 88%, IoU 85% | (unverified) |

---

## 3. Papers by task

### 3.1 Point / glyph detection (priority 1)

#### P1. Automatic vectorization of point symbols on archive maps using deep convolutional neural network
- **Authors / year / venue:** Vassányi, G. & Gede, M., 2021 (published 2021-12-03), *Proceedings of the ICA* 4:109. [doi:10.5194/ica-proc-4-109-2021](https://doi.org/10.5194/ica-proc-4-109-2021)
- **Overview:** The authors trained an instance-segmentation network to find small map symbols on old Austro-Hungarian military survey sheets, then turned each detection into a vector point. It is one of the few papers that targets point symbols directly instead of lines or areas ([abstract](https://doi.org/10.5194/ica-proc-4-109-2021)).
- **Category:** Point/glyph detection.
- **Training data:** Third Military Survey map sheets, four point-symbol categories, trained together. Mask R-CNN with a ResNet-101 + FPN backbone, run in Google Colab ([abstract](https://doi.org/10.5194/ica-proc-4-109-2021)). Number of annotations and annotation method: (unverified).
- **Validation/test:** A complete test sheet.
- **Results:** About 90% accuracy. For some categories, 94% of the symbols on the complete test sheet were detected ([abstract](https://doi.org/10.5194/ica-proc-4-109-2021)).
- **Code/data:** (unverified).
- **Locations:** Instance masks and boxes in pixel space, turned into vector points. The sheets were georeferenced separately (details unverified).

#### P2. Leveraging Deep Convolutional Neural Network for Point Symbol Recognition in Scanned Topographic Maps
- **Authors / year / venue:** Huang, W. et al., 2023 (2023-03-16), *ISPRS Int. J. Geo-Information* 12(3):128. [doi:10.3390/ijgi12030128](https://doi.org/10.3390/ijgi12030128)
- **Overview:** The authors adapted the YOLOv4 object detector to find and classify point symbols on scanned large-scale Chinese topographic maps. They replaced its pooling module with ASPP to capture context at several scales, and fitted anchor boxes to symbol sizes with k-means++. They also designed two map-specific augmentations to cope with rotation and with differences between data sources ([abstract via Semantic Scholar](https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/ijgi12030128?fields=abstract)).
- **Category:** Point/glyph detection.
- **Training data:** 1,909 scanned map images plus 2,505 images rendered from vector maps. The symbols follow the Chinese 1:500/1:1000/1:2000 topographic map specification (reported in the [article](https://www.mdpi.com/2220-9964/12/3/128); read through a search summary because the MDPI full text was blocked here). Partly synthetic, since some images are rendered from vector data.
- **Validation/test:** mAP and IoU. Cross-domain tests between scanned and vector-rendered images ([abstract](https://doi.org/10.3390/ijgi12030128)).
- **Results:** ASPP raised mAP and IoU over plain YOLOv4, and the augmentations helped cross-domain and rotation robustness. Exact numbers: (unverified).
- **Code/data:** (unverified).
- **Locations:** Bounding boxes in pixel coordinates.

#### P3. You Only Look for a Symbol Once (YOLSO): An Object Detector for Symbols and Regions in Documents
- **Authors / year / venue:** Smith, W.A.P. & Pillatt, T., 2023, ICDAR 2023 (LNCS), pp. 227–243. [doi:10.1007/978-3-031-41734-4_14](https://doi.org/10.1007/978-3-031-41734-4_14) · [accepted version](https://eprints.whiterose.ac.uk/id/eprint/198859/)
- **Overview:** Map symbols are usually drawn at a fixed size, so YOLSO only predicts each symbol's **centre** and class on a grid, not its box size. It is fully convolutional with no padding, so it can run on a whole map tile of any size. The same network also produces a coarse segmentation of regions marked by repeated symbols, such as woodland ([paper](https://eprints.whiterose.ac.uk/id/eprint/198859/)).
- **Category:** Point/glyph detection (plus coarse area segmentation).
- **Training data:** Ordnance Survey 1st-edition 1:2500 County Series (1890–1893), 135 randomly chosen 1 km² GeoTIFF tiles from historic Yorkshire (4724 or 6000 px square). There are 22,882 tree points (broadleaf/conifer) and 782 woodland polygons in 4 classes. Points were clicked by hand, then refined with template matching inside a 96 px window. Regions were drawn as polygons in GIS ([paper §4.1](https://eprints.whiterose.ac.uk/id/eprint/198859/)). Not synthetic.
- **Validation/test:** Held-out regions. A point counts as correct if the class is right and IoU > 0.5.
- **Results:** Point mAP@0.5 of 97.9% for YOLSO, against 43.6% for YOLOv3 and 70.2% for Faster R-CNN. Region mAP of 94.6% ([paper Table 1](https://eprints.whiterose.ac.uk/id/eprint/198859/)).
- **Code/data:** The abstract says the dataset and code are public. The repository URL was not found in the accepted manuscript (unverified).
- **Locations:** Symbol centres as **keypoints** in pixel space. The input tiles are already on the British National Grid, so pixels convert directly to georeferenced points.

#### P4. Accurate Feature Extraction from Historical Geologic Maps Using Open-Set Segmentation and Detection
- **Authors / year / venue:** Saxton, A. et al., 2024 (2024-11-13), *Geosciences* 14(11):305. [doi:10.3390/geosciences14110305](https://doi.org/10.3390/geosciences14110305)
- **Overview:** Each geologic map has its own legend, so the model takes the legend swatch (the "map unit") as a **prompt**. It then segments every matching polygon or detects every matching point symbol on the map ("one-shot", open-set). A human-in-the-loop tool lets geologists fix results ([abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.3390/geosciences14110305?fields=abstract)).
- **Category:** Point/glyph detection plus area/polygon extraction.
- **Training data:** Geologic maps annotated by USGS and DARPA for the AI4CMA challenge ([abstract](https://doi.org/10.3390/geosciences14110305)). Exact counts: (unverified).
- **Validation/test:** AI4CMA maps, median F1 (the challenge metric).
- **Results:** Median F1 of 0.91 for polygons and 0.73 for points, "when such features had abundant annotated data" ([abstract](https://doi.org/10.3390/geosciences14110305)). Rare point symbols are still limited by training data ([MDPI review report](https://www.mdpi.com/2076-3263/14/11/305/review_report)).
- **Code/data:** (unverified).
- **Locations:** Pixel masks for polygons and detections for points, in pixel space.

#### P5. Application of deep learning for symbol detection on historical maps to explore spatiotemporal changes in the regional tea industry of early 20th-century Taiwan
- **Authors / year / venue:** Pai, P.-L. et al., 2025 (2025-09-28), *Digital Scholarship in the Humanities*. [doi:10.1093/llc/fqaf099](https://doi.org/10.1093/llc/fqaf099)
- **Overview:** The authors trained a YOLO symbol detector to pull land-use symbols, in particular tea plantations, out of Taiwanese maps from the 1900s and 1920s. They then used the detected symbols in GIS to track how the tea industry changed ([abstract](https://doi.org/10.1093/llc/fqaf099)). It is a good example of point-symbol detection used as an applied history tool.
- **Category:** Point/glyph detection.
- **Training data:** Historical maps of the Tamsui area from the 1900s and 1920s ([abstract](https://doi.org/10.1093/llc/fqaf099)). Sizes: (unverified). The paper reportedly tried YOLOv8n and YOLOv8m and found accuracy fell when symbols were overlapped by contour lines (search summary of the article; unverified).
- **Validation/test / results:** (unverified).
- **Code/data:** Open access article (CC BY-NC). Code: (unverified).
- **Locations:** Bounding boxes, then turned into GIS points on georeferenced maps (unverified).

#### P6. Automated Detection and Encoding of Cartographic Signs in Historical Maps (CaSiDD) — *preprint*
- **Authors / year / venue:** Petitpierre, R., 2026 (arXiv v1 2026-10-09). [arXiv:2610.13224](https://arxiv.org/abs/2610.13224). Not yet peer reviewed.
- **Overview:** This is a two-step, style-agnostic approach. First, find *any* cartographic sign (class-agnostic) with YOLOv10-X. Then compute an embedding of each sign so that similar signs cluster across very different map styles. It also releases CaSiDD, a benchmark for generic sign detection ([abstract](https://arxiv.org/abs/2610.13224), [HTML](https://arxiv.org/html/2610.13224)).
- **Category:** Point/glyph detection.
- **Training data:** CaSiDD has 18,750 sign labels on 796 patches (768–1000 px) sampled from the Semap aggregator, which covers 20+ library portals in 5 countries. Labels are manual and class-agnostic, with 24 frequent categories where possible ([HTML](https://arxiv.org/html/2610.13224)).
- **Validation/test:** Precision and recall at IoU ≥ 0.3 and ≥ 0.5.
- **Results:** Class-agnostic detection: precision 81.1% and recall 41.5% at IoU ≥ 0.3, and 75.7% / 38.9% at IoU ≥ 0.5. The 24-class trial reached AP50 44.6% ([HTML](https://arxiv.org/html/2610.13224)). Recall is low, which shows how hard generic sign detection still is.
- **Code/data:** Dataset on Zenodo, [doi:10.5281/zenodo.16278380](https://doi.org/10.5281/zenodo.16278380). Dataset license and detector code: (unverified).
- **Locations:** Bounding boxes in pixel space.

*Point detection is also covered in DIGMAPPER (E2), which uses YOLOv8 with synthetic training patches.*

---

### 3.2 Area / polygon extraction (priority 2)

#### A1. Exploiting Polygon Metadata to Understand Raster Maps — Accurate Polygonal Feature Extraction
- **Authors / year / venue:** Lin, F., Knoblock, C.A., Shbita, B., Vu, B., Li, Z., Chiang, Y.-Y., 2023, ACM SIGSPATIAL 2023, pp. 1–12. [doi:10.1145/3589132.3625659](https://doi.org/10.1145/3589132.3625659)
- **Overview:** To find every area on a geologic map that belongs to a given rock unit, the model reads the map together with the legend's "map key" swatch. It encodes both as bitmaps and runs a CNN over them. This lets one model handle legends it has never seen ([ISI page](https://www.isi.edu/results/publications/19487/exploiting-polygon-metadata-to-understand-raster-maps-accurate-polygonal-feature-extraction/)).
- **Category:** Area/polygon extraction.
- **Training data:** USGS geologic maps. The group worked on the DARPA AI4CMA data, but the exact dataset and size are (unverified).
- **Validation/test:** USGS geologic maps, median F1.
- **Results:** Median F1 of 0.809, 4.52% above the prior state of the art ([ISI page](https://www.isi.edu/results/publications/19487/exploiting-polygon-metadata-to-understand-raster-maps-accurate-polygonal-feature-extraction/)).
- **Code/data:** (unverified).
- **Locations:** Pixel masks per legend item.

#### A2. Leveraging uncertainty estimation and spatial pyramid pooling for extracting hydrological features from scanned historical topographic maps
- **Authors / year / venue:** Wu, S., Heitzler, M., Hurni, L., 2022 (2022-01-06), *GIScience & Remote Sensing* 59(1):200–214. [doi:10.1080/15481603.2021.2023840](https://doi.org/10.1080/15481603.2021.2023840)
- **Overview:** The authors segment water features (such as streams and lakes) from old topographic maps with a U-Net plus ASPP. A Bayesian (uncertainty-aware) version also outputs a per-pixel "how sure am I" map, which highlights blurry boundaries, scan noise and unusual map designs ([abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1080/15481603.2021.2023840?fields=abstract)).
- **Category:** Area/polygon extraction (and thin water lines).
- **Training data:** Scanned historical topographic maps. Series and size: (unverified), but the authors' related work uses Swiss Siegfried maps.
- **Validation/test:** Dice coefficient.
- **Results:** Average Dice of 0.827, about 26% better than a plain U-Net ([abstract](https://doi.org/10.1080/15481603.2021.2023840)).
- **Code/data:** (unverified).
- **Locations:** Pixel masks plus pixel uncertainty maps.

#### A3. Domain adaptation in segmenting historical maps: A weakly supervised approach through spatial co-occurrence
- **Authors / year / venue:** Wu, S., Schindler, K., Heitzler, M., Hurni, L., 2023, *ISPRS J. Photogrammetry & Remote Sensing* 197:199–211. [doi:10.1016/j.isprsjprs.2023.01.021](https://doi.org/10.1016/j.isprsjprs.2023.01.021)
- **Overview:** A model trained on one map series often fails on an older or newer series. Maps of the same place across editions share many unchanged objects, so labels from one edition serve as rough (weak) labels for the other. This helps the model adapt without new hand labels ([ETH record](https://www.research-collection.ethz.ch/handle/20.500.11850/599929)).
- **Category:** Area/polygon extraction.
- **Training data:** Swiss Siegfried maps and old Swiss national maps (KOMB and KREL) ([ETH record](https://www.research-collection.ethz.ch/handle/20.500.11850/599929)). Sizes: (unverified).
- **Validation/test / results:** Weak supervision gives a "substantial benefit" over fully unsupervised domain adaptation (the authors' wording in the [ETH record](https://www.research-collection.ethz.ch/handle/20.500.11850/599929)). Numbers: (unverified).
- **Code/data:** Code at [github.com/sian-wusidi/spatialcooccurrence](https://github.com/sian-wusidi/spatialcooccurrence) (link reported in the ETH record).
- **Locations:** Pixel masks on georeferenced map sheets.

#### A4. Identifying wetland areas in historical maps using deep convolutional neural networks
- **Authors / year / venue:** Ståhl, N. & Weimann, L., 2022 (May), *Ecological Informatics* 68:101557. [doi:10.1016/j.ecoinf.2022.101557](https://doi.org/10.1016/j.ecoinf.2022.101557). The preprint came out Aug 2021 ([arXiv:2108.04107](https://arxiv.org/abs/2108.04107)); the journal version is inside the date window.
- **Overview:** A CNN marks wetlands on the Swedish "Generalstabskartan" military map. The model was then run across southern Sweden to make a historical wetland GIS layer ([arXiv abstract](https://arxiv.org/abs/2108.04107)).
- **Category:** Area/polygon extraction (land cover).
- **Training data:** Hand-labelled historical wetlands in Jönköping county from Generalstabskartan ([arXiv abstract](https://arxiv.org/abs/2108.04107)).
- **Validation/test:** 10-fold cross-validation, F1.
- **Results:** F1 of 0.886 ([arXiv abstract](https://arxiv.org/abs/2108.04107)).
- **Code/data:** The output GIS layer for southern Sweden is released as an open resource ([arXiv abstract](https://arxiv.org/abs/2108.04107)). Code: (unverified).
- **Locations:** Pixel classes on georeferenced sheets, exported as a GIS layer.

#### A5. Creating building-level, three-dimensional digital models of historic urban neighborhoods from Sanborn Fire Insurance maps using machine learning
- **Authors / year / venue:** Lin, Yue et al. (with H.J. Miller), 2023 (2023-06-28), *PLOS ONE* 18(6):e0286340. [doi:10.1371/journal.pone.0286340](https://doi.org/10.1371/journal.pone.0286340)
- **Overview:** On colour-coded US fire-insurance maps, a pixel classifier finds building footprints and their construction material from the map colours. Two Mask R-CNN models read small handwritten labels for building use and number of storeys. The results are combined into 3D models of neighbourhoods destroyed by highway building ([full text via Europe PMC](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10306198/fullTextXML)).
- **Category:** Area/polygon extraction (plus symbol/label detection).
- **Training data:** 13 Sanborn sheets (1961) for two Columbus, Ohio neighbourhoods. Labelled pixel regions train an SVM. Hand-labelled abbreviation and numeral boxes train the Mask R-CNN models (e.g. more than 11,000 "1-storey" numerals) ([full text](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10306198/fullTextXML)).
- **Validation/test:** Precision, recall and F1 on held-out pixel and label sets.
- **Results:** F1 of about 0.9 for footprints and materials, and above 0.7 for building use and storey count ([abstract](https://doi.org/10.1371/journal.pone.0286340)).
- **Code/data:** Code and data at [doi:10.6084/m9.figshare.22637848](https://doi.org/10.6084/m9.figshare.22637848).
- **Locations:** Sheets were georeferenced first, with control points from an address geocoder, so outputs are **georeferenced polygons**.

#### A6. MapSAM: adapting Segment Anything Model for automated feature detection in historical maps
- **Authors / year / venue:** Xia, X., Zhang, D., Song, W., Huang, W., Hurni, L., 2025 (2025-04-28), *GIScience & Remote Sensing*. [doi:10.1080/15481603.2025.2494883](https://doi.org/10.1080/15481603.2025.2494883) · [arXiv:2411.06971](https://arxiv.org/abs/2411.06971)
- **Overview:** The authors adapt Meta's Segment Anything Model (SAM) to historical maps with light fine-tuning (DoRA). They add automatic prompts, so no human clicking is needed. The goal is decent segmentation from very few labelled tiles ([abstract](https://arxiv.org/abs/2411.06971)).
- **Category:** Area/polygon and line extraction.
- **Training data:** Swiss Siegfried map, 224×224 tiles, hand-labelled binary masks. Railways: 5,872 train / 839 val / 1,679 test tiles, with 10%, 1% and 10-shot subsets. Vineyards: 613 / 87 / 177 tiles ([arXiv HTML](https://arxiv.org/html/2411.06971v1)). The journal version adds a building-block task ([journal abstract](https://doi.org/10.1080/15481603.2025.2494883)).
- **Validation/test:** IoU and F1.
- **Results (IoU, arXiv v1):** Railway with 10 training tiles: MapSAM 78.5 vs U-Net 61.4. With full data, U-Net is better (91.9 vs 89.5). Vineyard 10-shot: 60.0 vs U-Net 60.2 ([arXiv HTML](https://arxiv.org/html/2411.06971v1)). **Takeaway: foundation models help most when labels are very scarce.**
- **Code/data:** Code announced at [github.com/Xue-Xia/MapSAM](https://github.com/Xue-Xia/MapSAM). Data announced at [doi:10.3929/ethz-b-000691430](https://doi.org/10.3929/ethz-b-000691430) ([arXiv HTML](https://arxiv.org/html/2411.06971v1)).
- **Locations:** Pixel masks.

#### A7. Semantic Segmentation for Sequential Historical Maps by Learning from Only One Map — *preprint*
- **Authors / year / venue:** Yuan, Y., Thiemann, F., Sester, M., 2025 (arXiv 2025-01-03). [arXiv:2501.01845](https://arxiv.org/abs/2501.01845)
- **Overview:** The authors label one map edition by hand and train a U-Net. Its predictions then serve as pseudo-labels for the next-older and next-newer editions, step by step ("age-tracing"), with uncertain pixels filtered out ([abstract](https://arxiv.org/abs/2501.01845)).
- **Category:** Area/polygon extraction (land use).
- **Training data:** New "Hameln" dataset: German 1:25k topographic sheets 3821, 3822, 3921 and 3922 covering 1897–2017. Classes are woodland, grassland, settlement, flowing water, standing water and unknown. Mostly hand-annotated, rectified to UTM at 1 m/pixel ([HTML](https://arxiv.org/html/2501.01845v1)).
- **Validation/test:** Sheet 3922. mIoU and overall accuracy.
- **Results:** Best mIoU 77.3% (about 20 points over the baseline). Average overall accuracy 97% ([abstract](https://arxiv.org/abs/2501.01845)).
- **Code/data:** (unverified).
- **Locations:** Pixel masks on georeferenced (UTM) rasters.

#### A8. Leveraging LLMs and attention-mechanism for automatic annotation of historical maps — *preprint*
- **Authors / year / venue:** Yuan, Y. & Sester, M., 2025 (arXiv 2025-04-15). [arXiv:2504.11050](https://arxiv.org/abs/2504.11050)
- **Overview:** A large language model labels low-resolution map patches coarsely (for example, "this patch has woods"). An attention mechanism then sharpens these into finer masks, so no fine hand labels are needed ([abstract](https://arxiv.org/abs/2504.11050)).
- **Category:** Area/polygon extraction (labelling aid).
- **Training data:** Historical map patches, LLM-generated labels. Sizes: (unverified).
- **Results:** Recall above 90%. IoU of 84.2% (wood) and 72.0% (settlement). Precision of 87.1% and 79.5% ([abstract](https://arxiv.org/abs/2504.11050)).
- **Code/data:** (unverified).
- **Locations:** Pixel masks.

#### A9. Mapping Historic Urban Footprints in France: Balancing Quality, Scalability and AI Techniques — *preprint*
- **Authors / year / venue:** Rabehi, W., Le Texier, M., Lemoy, R., 2025 (arXiv 2025-10-02, v2 2026-03-09). [arXiv:2510.02097](https://arxiv.org/abs/2510.02097)
- **Overview:** A two-pass U-Net maps urban areas across all of metropolitan France from the IGN "Scan Histo" maps (1925–1950). The first pass finds confusing things such as text and roads. The second pass uses that to cut false positives ([abstract](https://arxiv.org/abs/2510.02097)).
- **Category:** Area/polygon extraction.
- **Training data:** Initial and refined training sets (sizes unverified).
- **Validation/test / results:** 941 high-resolution tiles processed. Overall accuracy of the final mosaic is 73% ([abstract](https://arxiv.org/abs/2510.02097)).
- **Code/data:** The authors say code, training data and the national raster are released. Links: (unverified).
- **Locations:** A georeferenced raster mosaic.

#### A10. MapReader: A Computer Vision Pipeline for the Semantic Exploration of Maps at Scale
- **Authors / year / venue:** Hosseini, K., Wilson, D.C.S., Beelen, K., McDonough, K., 2022, ACM SIGSPATIAL GeoHumanities '22. [doi:10.1145/3557919.3565812](https://doi.org/10.1145/3557919.3565812) · [arXiv:2111.15592](https://arxiv.org/abs/2111.15592) (v1 2021-11-30). Software paper: [JOSS doi:10.21105/joss.06434](https://doi.org/10.21105/joss.06434).
- **Overview:** Instead of drawing exact outlines, MapReader cuts each sheet into small square patches (about 100 m) and classifies each patch, for example "railspace" or "building". This is cheap to label and scales to whole national map series. The library now also includes a text-spotting pipeline ([README](https://github.com/maps-as-data/MapReader)).
- **Category:** Area extraction (coarse, patch-level). Text spotting in later versions.
- **Training data:** About 16K 19th-century Ordnance Survey sheets (about 30.5M patches). 62,020 hand-labelled patches in 4 classes (none / railspace / building / railspace+building) ([arXiv](https://ar5iv.labs.arxiv.org/html/2111.15592)).
- **Validation/test:** 12,404 val and 12,404 test patches.
- **Results:** ResNeSt-101e test F1-macro of 97.17% and F1-micro of 99.55% ([arXiv](https://ar5iv.labs.arxiv.org/html/2111.15592)).
- **Code/data:** [github.com/maps-as-data/MapReader](https://github.com/maps-as-data/MapReader). The paper says the labelled patches were released.
- **Locations:** A label per patch. Patch centres are converted to lat/lon from the sheet corner coordinates ([arXiv](https://ar5iv.labs.arxiv.org/html/2111.15592)).

---

### 3.3 Line extraction (roads, railways, faults)

#### L1. Towards the automated large-scale reconstruction of past road networks from historical maps
- **Authors / year / venue:** Uhl, J.H., Leyk, S., Chiang, Y.-Y., Knoblock, C.A., 2022 (June), *Computers, Environment and Urban Systems* 94:101794. [doi:10.1016/j.compenvurbsys.2022.101794](https://doi.org/10.1016/j.compenvurbsys.2022.101794)
- **Overview:** The method starts from today's road network and asks, segment by segment, "was this road already on the old map?". It answers using colour information from the georeferenced old map, with image processing and clustering ([abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.compenvurbsys.2022.101794?fields=abstract)).
- **Category:** Line extraction.
- **Training data:** Over 300,000 modern road segments (more than 50,000 km) and 42 USGS historical topographic sheets (1890–1950) in three US study areas. Mostly unsupervised clustering ([abstract](https://doi.org/10.1016/j.compenvurbsys.2022.101794)).
- **Validation/test:** Other historical datasets and manually made reference data. F1.
- **Results:** F1 up to 0.95 ([abstract](https://doi.org/10.1016/j.compenvurbsys.2022.101794)).
- **Code/data:** (unverified).
- **Locations:** Georeferenced vector road segments, because the method reuses modern geometries.

#### L2. A fast and effective deep learning approach for road extraction from historical maps by automatically generating training data with symbol reconstruction
- **Authors / year / venue:** Jiao, C., Heitzler, M., Hurni, L., 2022 (Sept), *Int. J. Applied Earth Observation & Geoinformation* 113:102980. [doi:10.1016/j.jag.2022.102980](https://doi.org/10.1016/j.jag.2022.102980)
- **Overview:** Hand-labelling roads is slow, so the authors **draw fake "imitation maps"** by re-rendering vector road data in the Siegfried map's symbol style, which gives labels for free. Models trained on these alone work reasonably well, and mixing them with a few real labels can beat real labels alone ([abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1016/j.jag.2022.102980?fields=abstract)).
- **Category:** Line extraction.
- **Training data:** Swiss Siegfried map. Four training scenarios with real data, synthetic data and mixes. Sizes: (unverified).
- **Results:** See overview. Numbers: (unverified).
- **Code/data:** (unverified).
- **Locations:** Pixel masks on georeferenced sheets.

#### L3. A novel framework for road vectorization and classification from historical maps based on deep learning and symbol painting
- **Authors / year / venue:** Jiao, C., Heitzler, M., Hurni, L., 2024 (March), *CEUS* 108:102060. [doi:10.1016/j.compenvurbsys.2023.102060](https://doi.org/10.1016/j.compenvurbsys.2023.102060)
- **Overview:** First, deep learning finds the road pixels. These are turned into vector lines. Each line is then classified by road type by "painting" each candidate road symbol over it and checking which matches best, so no class labels are needed (description from the follow-up paper, [arXiv:2410.02250](https://arxiv.org/abs/2410.02250)).
- **Category:** Line extraction (vectorization and classification).
- **Training / eval / results:** Siegfried map. Details: (unverified; abstract not retrievable here).
- **Code/data:** (unverified).
- **Locations:** Vector polylines with class attributes.

#### L4. Contrastive Pretraining for Railway Detection: Unveiling Historical Maps with Transformers
- **Authors / year / venue:** Xia, X., Jiao, C., Hurni, L., 2023 (2023-11-13), ACM SIGSPATIAL GeoAI '23 workshop. [doi:10.1145/3615886.3627738](https://doi.org/10.1145/3615886.3627738)
- **Overview:** The same Swiss location appears on both the Siegfried map and the later Old National Map. The authors treat such pairs as "the same scene" and pre-train a transformer without labels (contrastive learning), then fine-tune it to find railways ([abstract](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/3615886.3627738?fields=abstract)).
- **Category:** Line extraction.
- **Training data:** Siegfried and Old National Map tile pairs (self-supervised), plus a small labelled set.
- **Results:** Matches fully supervised performance with only **2.5%** of the labelled data ([abstract](https://doi.org/10.1145/3615886.3627738)).
- **Code/data:** (unverified).
- **Locations:** Pixel masks.

#### L5. Probabilistic road classification in historical maps using synthetic data and deep learning — *preprint*
- **Authors / year / venue:** Mühlematter, D.J. et al., 2024 (arXiv 2024-10-03). [arXiv:2410.02250](https://arxiv.org/abs/2410.02250)
- **Overview:** The method extracts road lines, then classifies each road using a model ensemble trained on roads **re-painted** in each class's symbol style. It outputs class probabilities instead of hard labels ([abstract](https://arxiv.org/abs/2410.02250)).
- **Category:** Line extraction.
- **Training data:** Synthetic re-painted Siegfried roads. No manual class labels.
- **Validation/test:** Two Siegfried sheets. Completeness and correctness.
- **Results:** Road class 2 (most common): completeness above 94% and correctness above 92% ([abstract](https://arxiv.org/abs/2410.02250)).
- **Code/data:** (unverified).
- **Locations:** Vector road geometries with class probabilities.

#### L6. Deep learning-based extraction of Kenya's historical road network from topographic maps
- **Authors / year / venue:** Kramm, T. et al., 2025 (2025-07-05), *Scientific Data* 12:1149. [doi:10.1038/s41597-025-05442-6](https://doi.org/10.1038/s41597-025-05442-6)
- **Overview:** This is a national-scale, practical workflow. The team scanned and hand-georeferenced 533 Kenyan topographic sheets. They then trained one segmentation model per road symbol type with ArcGIS Pro's "Multi-Task Road Extractor" and merged the results into one road dataset ([full text](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12228767/fullTextXML)).
- **Category:** Line extraction.
- **Training data:** 533 maps at 1:50,000 and 1:100,000 (1950s–1980s), with 20 road symbols in 3 groups. Labels were hand-digitized road lines buffered by 20 m and exported as 512×512 chips with 128 px overlap. The model is a U-Net with a ResNet34 backbone ("hourglass") ([full text](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12228767/fullTextXML)).
- **Validation/test:** Manually digitized roads on 7 representative sheets. Overall accuracy, precision, recall, F1, IoU and positional deviation.
- **Results:** Average F1 of 0.84. More than 56,000 km of roads ([abstract](https://doi.org/10.1038/s41597-025-05442-6)).
- **Code/data:** Data under CC BY 4.0 at [doi:10.5880/TRR228DB.37](https://doi.org/10.5880/TRR228DB.37). Scripts at [doi:10.5880/TRR228DB.32](https://doi.org/10.5880/TRR228DB.32). They need commercial ArcGIS Pro ([full text](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12228767/fullTextXML)).
- **Locations:** Georeferenced vector lines (UTM / Arc 1960).

*Geologic fault lines are covered in DIGMAPPER (E2).*

---

### 3.4 OCR / map text spotting (priority 3, extra depth)

**Why maps are hard for OCR.** Map text is often curved or rotated. It can be spaced very widely with other symbols in between, printed in old or engraved fonts, or handwritten. It sits on busy backgrounds and changes size and style to show feature type. A single place name can also be split across several separate words that are far apart ([MapText 2024 report §1](https://weinman.cs.grinnell.edu/pubs/li24icdar.pdf)). So the field splits into three sub-tasks: **detection** (polygon around each word), **recognition** (the text string), and **linking** (grouping and ordering words into place-name phrases).

**Background (before the date window, for context only).** *Strabo* (USC Spatial Computing group, about 2014–2018) was an earlier map text recognition toolkit ([GitHub](https://github.com/spatial-computing/strabo-text-recognition)). It is older than this review's window and has been replaced by deep text spotters such as mapKurator (T4). The SynthMap synthetic-data paper by Kim et al. appeared at GeoAI '21 (November 2021). Its arXiv version is [2112.06104](https://arxiv.org/abs/2112.06104), but the venue date is before the cutoff, so it is not counted. Its successor, SynthMap+, is covered in T3.

#### T1. ICDAR 2024 Competition on Historical Map Text Detection, Recognition, and Linking (MapText 2024)
- **Authors / year / venue:** Li, Z., Lin, Y., Chiang, Y.-Y., Weinman, J., Tual, S., Chazalon, J., Perret, J., Duménieu, B., Abadie, N., 2024, ICDAR 2024 (LNCS). [doi:10.1007/978-3-031-70552-6_22](https://doi.org/10.1007/978-3-031-70552-6_22) · [accepted manuscript](https://weinman.cs.grinnell.edu/pubs/li24icdar.pdf)
- **Overview:** This is the first shared benchmark for reading text on historical maps. It has four tasks: word detection, phrase detection (word linking), word detection + recognition, and phrase detection + recognition. Each is scored on a broad English set and a narrow French handwritten cadastral set. It received 44 submissions from 8 teams ([report](https://weinman.cs.grinnell.edu/pubs/li24icdar.pdf)).
- **Category:** OCR/text spotting and linking.
- **Training data:** **Rumsey**: 936 maps chosen by style clustering from the David Rumsey collection (80 regions, 183 publication years, 1623–2012). They are cut into 2000×2000 tiles, with 200 train tiles (34,518 words), 40 val and 700 test. **French Land Registers**: 19th-century cadastral plans of about 50 towns, mostly handwritten and many numbers; 145 sheets with more than 17,000 words, split by town. Annotations are word polygons, transcriptions, groups, and illegible/truncated flags ([report §3, Table 1](https://weinman.cs.grinnell.edu/pubs/li24icdar.pdf)).
- **Metrics:** IoU > 0.5 matching. Panoptic Detection Quality (PDQ = tightness × F), Panoptic Word Quality (PWQ, which needs an exact transcription), and Panoptic Character Quality (PCQ = T × F × (1 − normalized edit distance)) ([report §2](https://weinman.cs.grinnell.edu/pubs/li24icdar.pdf)).
- **Headline results:**
  - Rumsey word detection: the best was the Bilibili "MapText Detection Strong Pipeline" (DeepSolo + ViTAEv2-S, trained only on public scene-text data) at PDQ 76.1, F 92.0. A fine-tuned MaskDINO object detector was close at 73.4.
  - Rumsey word recognition: the best PWQ was 60.1. Phrase-level PCQ was only 33.1.
  - French: the best word recognition PWQ was 40.1 (MapTest: PP-YOLOE-R + ABINet).
  - The TESTR baseline scored PDQ 55.1 (Rumsey).
  ([report Tables 2–5](https://weinman.cs.grinnell.edu/pubs/li24icdar.pdf))
- **Code/data:** Evaluation code at [github.com/icdar-maptext/evaluation](https://github.com/icdar-maptext/evaluation) (GPL-3.0). Rumsey train/val at [Zenodo 10608901](https://zenodo.org/records/10608901) (CC BY-NC-SA 3.0, per the Zenodo API). The live leaderboard is on the [RRC platform](https://rrc.cvc.uab.es/?ch=28). The winning Rumsey pipeline is at [github.com/yyyyyxie/MapTextPipeline](https://github.com/yyyyyxie/MapTextPipeline), based on DNTextSpotter ([arXiv:2408.00355](https://arxiv.org/abs/2408.00355), ACM MM 2024).
- **Locations:** Word **polygons** in tile pixel coordinates (not georeferenced).

#### T2. ICDAR 2025 Competition on Historical Map Text Detection, Recognition, and Linking (MapText 2025)
- **Authors / year / venue:** Lin, Y., Tual, S., Li, Z., Jang, L., Chiang, Y.-Y., Weinman, J., Chazalon, J., Carlinet, E., Perret, J., Abadie, N., Duménieu, B., et al., 2025, ICDAR 2025 (LNCS 16027). [doi:10.1007/978-3-032-04630-7_33](https://doi.org/10.1007/978-3-032-04630-7_33) · [accepted manuscript](https://weinman.cs.grinnell.edu/~weinman/pubs/lin25icdar.pdf)
- **Overview:** The second edition keeps the Rumsey set and adds three things: more than twice as many French land-register tiles, a new **Taiwanese topographic map set in traditional Chinese** (1900–1960, 1:20k–1:50k, horizontal and vertical text), and **synthetic training data for each dataset**. It also changed the metrics. In 2024 the winner of the linking task predicted *no links at all* and still won, so 2025 scores link precision and recall explicitly ([report §1–3](https://weinman.cs.grinnell.edu/~weinman/pubs/lin25icdar.pdf)).
- **Category:** OCR/text spotting and linking.
- **Training data:** Rumsey (unchanged), expanded French (228 sheets total, plus 18,073 synthetic tiles from an open generator), and Taiwanese (311 of about 1,205 sheets annotated; train on 1904/1905/1921 sheets, val on 1924, test on the 1950s) plus a Chinese synthetic set. English synthetic data (SynthMap+, 35,000 tiles) is at [Zenodo 14480731](https://zenodo.org/records/14480731) (CC BY 4.0) ([report §3](https://weinman.cs.grinnell.edu/~weinman/pubs/lin25icdar.pdf)).
- **Metrics:** Harmonic mean of detection precision, recall, tightness, character accuracy (1 − NED), and link precision/recall, depending on the task ([report §2](https://weinman.cs.grinnell.edu/~weinman/pubs/lin25icdar.pdf)).
- **Headline results:**
  - Rumsey word detection: H-mean 90.2 (MapText Strong Pipeline, DNTextSpotter).
  - Rumsey phrase detection: H-mean 78.4, a tie between EPFL's "Self-Sequencer" (DeepSolo + a transformer linker) and NAVER/LINE's "CREPE + BezierCurve" (a Donut-style end-to-end model that outputs Bézier control points, with no post-processing).
  - A fine-tuned TESTR baseline was a strong detector, especially on French data.
  ([report Tables 3–4](https://weinman.cs.grinnell.edu/~weinman/pubs/lin25icdar.pdf))
- **Code/data:** All resources are at [zenodo.org/communities/icdar-maptext](https://zenodo.org/communities/icdar-maptext). IGN 2025 train/val is at [Zenodo 14392548](https://zenodo.org/records/14392548) (CC BY-SA 4.0). The French synthetic generator is at [doi:10.5281/zenodo.15498600](https://doi.org/10.5281/zenodo.15498600) (LGPL-3.0). The RRC page is [ch=32](https://rrc.cvc.uab.es/?ch=32).
- **Locations:** Word polygons in pixel space, grouped into ordered phrases.

#### T3. Hyper-Local Deformable Transformers for Text Spotting on Historical Maps (PALETTE) + SynthMap+
- **Authors / year / venue:** Lin, Y. & Chiang, Y.-Y., 2024, KDD 2024, pp. 5387–5397. [doi:10.1145/3637528.3671589](https://doi.org/10.1145/3637528.3671589) (DOI as given on [Zenodo 14480731](https://zenodo.org/records/14480731)) · [arXiv:2506.15010](https://arxiv.org/abs/2506.15010)
- **Overview:** PALETTE is an end-to-end text spotter (detect + read in one model) built on a deformable DETR. It samples image features very close to each text boundary point and each character ("hyper-local"), which helps with long and steeply rotated map labels. It is trained mainly on **SynthMap+**: synthetic maps that place real OpenStreetMap names along real features using QGIS label placement, on backgrounds taken from Rumsey maps ([arXiv HTML](https://arxiv.org/html/2506.15010v1)).
- **Category:** OCR/text spotting.
- **Training data:** SynthMap+ (73,657 images, 1,102,940 text annotations), SynthText, then ICDAR15, Total-Text and MLT. Fine-tuning on Total-Text ([arXiv HTML](https://arxiv.org/html/2506.15010v1)).
- **Validation/test:** Grinnell-UMass-31 (500 tiles, 15,143 instances, from 31 Rumsey maps) and the new Rumsey-309 (309 tiles, 13,145 labels, from 54 maps). Detection P/R/F and end-to-end F1 with and without a lexicon ([arXiv HTML](https://arxiv.org/html/2506.15010v1)).
- **Results:** End-to-end F1 with no lexicon on Rumsey-309: PALETTE 69.82 vs TESTR 65.99 vs DeepSolo 60.11. On Grinnell-UMass-31: 70.27 vs 68.05. After fine-tuning on Rumsey-309: 75.87 ([arXiv HTML](https://arxiv.org/html/2506.15010v1)). Deployed on more than 60,000 Rumsey maps, producing more than 100M labels ([abstract](https://arxiv.org/abs/2506.15010)).
- **Code/data:** [github.com/kartta-foundation/mapkurator-palette-doc](https://github.com/kartta-foundation/mapkurator-palette-doc). SynthMap+ at [Zenodo 14480731](https://zenodo.org/records/14480731).
- **Locations:** 16-point text-boundary **polygons** in pixel space. They are georeferenced later by mapKurator (T4).

#### T4. The mapKurator System: A Complete Pipeline for Extracting and Linking Text from Historical Maps
- **Authors / year / venue:** Kim, J., Li, Z., Lin, Y., Namgung, M., Jang, L., Chiang, Y.-Y., 2023, ACM SIGSPATIAL 2023 (demo). [arXiv:2306.17059](https://arxiv.org/abs/2306.17059)
- **Overview:** mapKurator is a full, working pipeline. It (1) cuts big scans into tiles, (2) spots text in each tile, (3) merges tile results back into map coordinates, (4) fixes OCR errors by matching against OpenStreetMap place names, (5) converts pixels to geographic coordinates using the map's control points (GDAL), and (6) links each label to an OpenStreetMap entity ([arXiv HTML](https://arxiv.org/html/2306.17059v2)).
- **Category:** OCR/text spotting plus end-to-end (georeferenced output and entity linking).
- **Training data:** Synthetic scene text, a synthetic map dataset, and human-annotated real maps (sizes not stated) ([arXiv HTML](https://arxiv.org/html/2306.17059v2)).
- **Validation/test:** No new benchmark. Deployment at scale on more than 60,000 Rumsey maps with more than 100M labels ([arXiv](https://arxiv.org/abs/2306.17059)).
- **Code/data:** [github.com/knowledge-computing/mapkurator-system](https://github.com/knowledge-computing/mapkurator-system). Docs and Docker images at [knowledge-computing.github.io/mapkurator-doc](https://knowledge-computing.github.io/mapkurator-doc/).
- **Locations:** **Georeferenced GeoJSON polygons** with text, score, post-OCR text and OSM ID ([arXiv HTML](https://arxiv.org/html/2306.17059v2)).

#### T5. LIGHT: Multi-Modal Text Linking on Historical Maps
- **Authors / year / venue:** Lin, Y., Olson, R., Wu, J., Chiang, Y.-Y., Weinman, J., 2025, ICDAR 2025 (LNCS), pp. 60–77. [doi:10.1007/978-3-032-04617-8_4](https://doi.org/10.1007/978-3-032-04617-8_4) · [arXiv:2506.22589](https://arxiv.org/abs/2506.22589)
- **Overview:** Given words already found by a spotter, LIGHT predicts each word's "next word" in the same place name. It uses the text itself (language), the image, and the shape and position of each word's polygon (geometry). It is built on LayoutLMv3 with a new geometry encoder ([arXiv HTML](https://arxiv.org/html/2506.22589v2)).
- **Category:** OCR/text linking.
- **Training data:** MapText Rumsey (200 train + 40 val tiles). Pre-training on 397,385 tiles from 41,279 Rumsey maps, auto-labelled by a spotter ([arXiv HTML](https://arxiv.org/html/2506.22589v2)).
- **Validation/test:** 700 Rumsey test tiles. Link precision, recall and F.
- **Results:** Link F of 83.7 on ground-truth words, vs 77.8 for LayoutLMv3 (pretrain + finetune) and 44.3 for the heuristic MST. With spotter output it gains 19.9% over DS-LP and 7.8% over Self-Sequencer ([arXiv HTML](https://arxiv.org/html/2506.22589v2)). It is not end-to-end and depends on an external spotter ([arXiv](https://arxiv.org/abs/2506.22589)).
- **Code/data:** [github.com/knowledge-computing/multimodal-text-linking](https://github.com/knowledge-computing/multimodal-text-linking).
- **Locations:** Ordered word polygons (pixel space).

#### T6. Automatic Search of Multiword Place Names on Historical Maps
- **Authors / year / venue:** Olson, R., Kim, J., Chiang, Y.-Y., 2024, ACM SIGSPATIAL GeoSearch '24 workshop. [doi:10.1145/3681769.3698577](https://doi.org/10.1145/3681769.3698577) · [arXiv:2410.15586](https://arxiv.org/abs/2410.15586)
- **Overview:** This is a simple, training-free way to search for names such as "New York City" when the spotter only found single words. It links nearby words of similar height, angle and capitalization with a minimum spanning tree, then searches those trees ([abstract](https://arxiv.org/abs/2410.15586)).
- **Category:** OCR/text linking and search.
- **Eval data:** MapText 2024 data (940 tiles), with 5-fold cross-validation.
- **Results:** Link precision 26.15% and recall 82.61%, versus 25.33% / 82.28% for a character-distance baseline ([arXiv HTML](https://arxiv.org/html/2410.15586v2)). Retrieval over about 60,000 maps: on average 80 maps per query spanning about 205 years.
- **Code/data:** (unverified).
- **Locations:** Groups of word polygons.

#### T7. Recognizing and Sequencing Multi-word Texts in Maps Using an Attentive Pointer — *preprint*
- **Authors / year / venue:** Zou, M., Dai, T., Petitpierre, R., Vaienti, B., Kaplan, F., di Lenardo, I., 2025 (2025-04-15), Research Square preprint. [doi:10.21203/rs.3.rs-6330456/v1](https://doi.org/10.21203/rs.3.rs-6330456/v1) · [EPFL record](https://infoscience.epfl.ch/handle/20.500.14299/249929)
- **Overview:** A modular framework spots words and then uses a pointer network to link and *order* them into full multi-word names. It ignores "distractor" words in between by using position and Bézier-curve direction features. This method (the "Self-Sequencer") tied for first in MapText 2025 phrase detection ([MapText 2025 report](https://weinman.cs.grinnell.edu/~weinman/pubs/lin25icdar.pdf)).
- **Category:** OCR/text linking.
- **Training data:** For MapText 2025: ICDAR MapText, mapKurator human labels, SynthMap, and the Paris and Jerusalem Maps Text Dataset (82 annotated samples) ([MapText 2025 report](https://weinman.cs.grinnell.edu/~weinman/pubs/lin25icdar.pdf)).
- **Results:** Applied to the 1890s Ordnance Survey of London, it retrieved 285,846 text sequences. The geocoded names were used to realign city maps automatically ([EPFL record abstract](https://infoscience.epfl.ch/handle/20.500.14299/249929)).
- **Code/data:** CC BY preprint. Code: (unverified).
- **Locations:** Ordered word polygons. Also geocoded names.

*Text is also central to G1, G3, A5 and E2.*

---

### 3.5 Georeferencing

#### G1. Automatic Georeferencing of Topographic Raster Maps
- **Authors / year / venue:** Milleville, K., Verstockt, S., Van de Weghe, N., 2022 (2022-07-11), *ISPRS IJGI* 11(7):387. [doi:10.3390/ijgi11070387](https://doi.org/10.3390/ijgi11070387)
- **Overview:** The method reads the place names on a map with pretrained OCR and looks them up with public geocoders. The matches give control points, which fix the map's position on Earth ([abstract via Crossref](https://api.crossref.org/works/10.3390/ijgi11070387)).
- **Category:** Georeferencing (text-based).
- **Training data:** None new (pretrained OCR).
- **Eval:** 16 historical and 9 modern topographic maps (1:25k and 1:50k, Belgium/Netherlands per [search summary](https://www.mdpi.com/2220-9964/11/7/387); region unverified).
- **Results:** Mean error of 316 m (1.67%) on historical maps and 287 m (0.90%) on modern maps ([abstract](https://doi.org/10.3390/ijgi11070387)).
- **Code/data:** (unverified).
- **Locations:** Map → world transform from geocoded text positions.

#### G2. Georeferencing historical maps using local feature matching and Delaunay consistency
- **Authors / year / venue:** Vaienti, B., di Lenardo, I., Kaplan, F., 2025 (2025-11-06), *Cartography and Geographic Information Science*. [doi:10.1080/15230406.2025.2566789](https://doi.org/10.1080/15230406.2025.2566789)
- **Overview:** If some maps of a city are already georeferenced ("anchors"), new maps can be matched to them. Learned keypoints (SuperPoint) are matched with SuperGlue, bad matches are filtered by checking that the triangle mesh (Delaunay) of matched points stays consistent, and the control points are passed on (method as summarized from the [article](https://www.tandfonline.com/doi/full/10.1080/15230406.2025.2566789) via search; full text not read).
- **Category:** Georeferencing (image matching, map-to-map; no imagery).
- **Training / eval / results:** (unverified; paywalled).
- **Code/data:** (unverified).
- **Locations:** Ground control points, then a warp.

#### G3. Automated Georeferencing of Topographic Maps via OCR and In-Context Multimodal LLM Reasoning
- **Authors / year / venue:** Tyagi & Dubey, 2026, *Communications in Computer and Information Science* (Springer). [doi:10.1007/978-3-032-08511-5_8](https://doi.org/10.1007/978-3-032-08511-5_8)
- **Overview:** EasyOCR finds the printed latitude/longitude tick labels around a topographic sheet. A two-step multimodal LLM interprets them, and an affine fit with outlier removal gives control points (from the publisher abstract snippet, read via search; unverified).
- **Eval / results:** 12 sheets. Internal RMSE under 5 m, and validation RMSE under 30 m on 11 maps (unverified, publisher snippet).
- **Code/data:** (unverified).
- **Locations:** GCPs from the map frame's coordinate labels.

*DIGMAPPER (E2) also includes georeferencing: corner-coordinate OCR + place-name lookup, then LightGlue matching against about 250K USGS topographic maps.*

---

### 3.6 End-to-end systems and vectorization

#### E1. Automatic vectorization of historical maps: A benchmark
- **Authors / year / venue:** Chen, Y., Chazalon, J., Carlinet, E., Ngoc, M.Ô.V., Mallet, C., Perret, J., 2024 (2024-02-15), *PLOS ONE* 19(2):e0298217. [doi:10.1371/journal.pone.0298217](https://doi.org/10.1371/journal.pone.0298217)
- **Overview:** The benchmark turns a scanned Paris city atlas into clean closed polygons (building blocks, parcels and so on). It tests many "edge detector + shape closing" combinations: deep edge networks (U-Net, HED, BDCN, ViT, PVT), topology-aware losses, and watershed shape extraction. The goal is to find what really matters ([article](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0298217)).
- **Category:** End-to-end vectorization (area/polygon).
- **Training data:** The Paris *Atlas Municipal* (1:5000), 1926 edition sheet, for training and validation. 8,362 hand-drawn polygons in total ([article](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0298217)).
- **Test:** An 1898-edition sheet. COCO panoptic quality (PQ).
- **Results:** U-Net with a better training protocol: 46.7% PQ. Joint optimization: 47.1%. Contrast + thin-plate-spline augmentation: **51.1%** (best). Transformers did not beat U-Net overall. A 4M-parameter mini U-Net scored 45.1% ([article](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0298217)).
- **Code/data:** [github.com/soduco/Benchmark_historical_map_vectorization](https://github.com/soduco/Benchmark_historical_map_vectorization). [Zenodo 10567765](https://zenodo.org/records/10567765) (CC BY 4.0).
- **Locations:** Closed polygons in pixel space.

#### E2. DIGMAPPER: A Modular System for Automated Geologic Map Digitization — *preprint (industry)*
- **Authors / year / venue:** Duan, W., Knoblock, C.A., Lin, F., Chen, T., Jang, L., Kirsanova, S., Li, Z., Lin, Y., Chiang, Y.-Y., Gerlek, M.P., Minton, S.N., 2025 (arXiv 2025-06-19). [arXiv:2506.16006](https://arxiv.org/abs/2506.16006). Listed as accepted to ACM SIGSPATIAL 2025 by a search result (unverified; the arXiv HTML has a placeholder venue).
- **Overview:** This is the most complete published "scan in, GIS layers out" system for geologic maps, built with USGS for critical-mineral work. Its parts are:
  - Layout analysis (LayoutLMv3) to find the map body and legend.
  - GPT-4o in-context learning to pair each legend swatch with its description.
  - Polygon extraction (TOPAZ: ViT + BERT + U-Net).
  - Fault-line extraction (LDTR, a graph transformer).
  - Point-symbol detection (YOLOv8).
  - Georeferencing.

  ([arXiv HTML](https://arxiv.org/html/2506.16006v1))
- **Category:** End-to-end (point, line, polygon, georeferencing).
- **Training data:** Points: about 10,000 synthetic 1000×1000 patches (about 3,000 per class) made by stamping FGDC-standard geologic symbols onto masked base maps, plus human labels from 100 USGS maps. Other modules: (unverified) ([arXiv HTML](https://arxiv.org/html/2506.16006v1)).
- **Eval and results** ([arXiv HTML](https://arxiv.org/html/2506.16006v1)):
  - Layout (40 maps): legend item F1 of 0.90 on "excellent" maps.
  - Polygons (11 maps, 221 legend items): F1 0.98 / 0.77 / 0.28 on excellent / good / fair-quality maps.
  - Faults (10 maps): about 0.88–0.94 correctness on excellent maps.
  - Points (10 maps, 5 symbol types): F1 0.82, vs 0.79 when trained on human labels only.
  - Georeferencing (63 maps): median 0.104 km RMSE.
- **Code/data:** Related CriticalMAAS code, e.g. [github.com/DARPA-CRITICALMAAS/uncharted-ta1](https://github.com/DARPA-CRITICALMAAS/uncharted-ta1) (MIT, Uncharted's team). A DIGMAPPER-specific repository was not found (unverified).
- **Locations:** Georeferenced vector polygons and lines with legend labels, plus points.

#### E3. Detecting Legend Items on Historical Maps Using GPT-4o with In-Context Learning — *preprint*
- **Authors / year / venue:** Kirsanova, S., Chiang, Y.-Y., Duan, W., 2025 (arXiv 2025-10-09). [arXiv:2510.08385](https://arxiv.org/abs/2510.08385)
- **Overview:** Reading the legend is step zero for legend-driven extraction. This paper uses LayoutLMv3 to find the legend area. GPT-4o, given a few worked examples in a structured JSON prompt, then returns boxes for each legend symbol and its description ([abstract](https://arxiv.org/abs/2510.08385)).
- **Category:** End-to-end support (legend parsing).
- **Eval / results:** USGS geologic maps. F1 88% and IoU 85% ([abstract](https://arxiv.org/abs/2510.08385)).
- **Code/data:** (unverified).
- **Locations:** Bounding boxes in pixel space.

---

## 4. Key datasets and benchmarks

| Dataset | What it contains | Size | License | Link |
|---|---|---|---|---|
| **ICDAR MapText – Rumsey** | Historical maps (1623–2012, worldwide, English), word polygons + transcriptions + phrase groups | 940 tiles of 2000×2000 (200 train / 40 val / 700 test); about 34.5K train words | CC BY-NC-SA 3.0 (train/val) | [Zenodo 10608901](https://zenodo.org/records/10608901), [report](https://weinman.cs.grinnell.edu/pubs/li24icdar.pdf) |
| **ICDAR MapText – French Land Registers (IGN)** | 19th-c. French cadastral plans, mostly handwritten text and parcel numbers | 2024: 145 sheets, more than 17K words; 2025: expanded to 228 sheets + 18,073 synthetic tiles | CC BY-SA 4.0 (2025 train/val) | [Zenodo 14392548](https://zenodo.org/records/14392548) |
| **ICDAR MapText – Taiwanese topographic maps** | 1900–1960 Taiwan, traditional Chinese, horizontal and vertical text | 311 annotated sheets of about 1,205 | (unverified) | [MapText community](https://zenodo.org/communities/icdar-maptext), [report](https://weinman.cs.grinnell.edu/~weinman/pubs/lin25icdar.pdf) |
| **SynthMap+ (English)** | Synthetic historical-style maps, with word and phrase labels | 35,000 tiles, 348,494 words (MapText release); the paper version has 73,657 images | CC BY 4.0 | [Zenodo 14480731](https://zenodo.org/records/14480731) |
| **Rumsey-309 / Grinnell-UMass-31** | Text spotting test sets from Rumsey maps | 309 tiles (13,145 labels) / 500 tiles (15,143) | (unverified) | [PALETTE paper](https://arxiv.org/html/2506.15010v1) |
| **Paris & Jerusalem Maps Text Dataset** | Historical city maps of Paris and Jerusalem; detection, recognition, sequencing | 82 annotated samples | (unverified) | Cited in the [MapText 2025 report](https://weinman.cs.grinnell.edu/~weinman/pubs/lin25icdar.pdf) |
| **DARPA/USGS AI4CMA competition data** | Scanned geologic and topographic maps. *Feature extraction*: per-legend-item binary rasters for points (1-pixel), fault lines (1-pixel wide) and polygons, plus JSON legend boxes. *Georeferencing*: separate challenge data | DIGMAPPER cites 48 annotated maps for feature extraction and 63 for georeferencing ([search summary of arXiv 2506.16006](https://arxiv.org/html/2506.16006v1)); full counts (unverified) | Public; data.usgs.gov lists public domain (via search summary) | [doi:10.5066/P9FXSPT1](https://doi.org/10.5066/P9FXSPT1), [challenge details PDF](https://criticalminerals.darpa.mil/Files/Map_Feature_Extraction_Challenge_Details.pdf) |
| **Paris Atlas vectorization benchmark** | Atlas Municipal de Paris (1898, 1926), closed-shape polygons | 8,362 polygons | CC BY 4.0 | [Zenodo 10567765](https://zenodo.org/records/10567765), [GitHub](https://github.com/soduco/Benchmark_historical_map_vectorization) |
| **ICDAR 2021 MapSeg (older, 2021)** | Paris atlas map segmentation and vectorization challenge (predates this review window; listed because E1 and much later work build on it) | (see E1) | CC BY 4.0 (dataset record) | [Zenodo 8325527](https://zenodo.org/records/8325527) |
| **CaSiDD** | Generic cartographic signs across collections | 796 patches, 18,750 sign boxes, 24 frequent categories | (unverified) | [doi:10.5281/zenodo.16278380](https://doi.org/10.5281/zenodo.16278380) |
| **YOLSO OS tree dataset** | OS 1st-edition 1:2500, Yorkshire: tree points + woodland polygons | 135 tiles, 22,882 points, 782 polygons | Underlying maps © Crown/Landmark; dataset license (unverified) | [paper](https://eprints.whiterose.ac.uk/id/eprint/198859/) |
| **MapReader OS patches** | 19th-c. OS patches labelled railspace/building | 62,020 labelled patches | (unverified) | [MapReader](https://github.com/maps-as-data/MapReader) |
| **MapSAM Siegfried sets** | Railway and vineyard masks | 8,390 railway tiles, 877 vineyard tiles | (unverified) | [doi:10.3929/ethz-b-000691430](https://doi.org/10.3929/ethz-b-000691430) |
| **Kenya historical roads** | Vector road network, 1950s–80s | 533 sheets, more than 56,000 km | CC BY 4.0 | [doi:10.5880/TRR228DB.37](https://doi.org/10.5880/TRR228DB.37) |
| **Sanborn Columbus** | Code + labelled data for footprints and labels | 13 sheets | (see figshare) | [doi:10.6084/m9.figshare.22637848](https://doi.org/10.6084/m9.figshare.22637848) |

---

## 5. Practical takeaways for building a map digitizer

### 5.1 Glyph / point-symbol localization
1. **Start with a standard detector, but predict centres.** Fine-tune YOLOv8/YOLOv10 on tiles of 512–1024 px (as in [DIGMAPPER](https://arxiv.org/html/2506.16006v1) and [CaSiDD](https://arxiv.org/html/2610.13224)). Map symbols have a fixed size per series, so consider YOLSO's idea of predicting only the **centre + class**. It beat YOLOv3 and Faster R-CNN by a wide margin on small, sparse symbols ([Smith & Pillatt 2023](https://eprints.whiterose.ac.uk/id/eprint/198859/)). The output you want is a keypoint, not a box.
2. **Make synthetic training data by stamping symbols.** Paste the legend or standard symbol glyphs onto real map backgrounds with the real symbols masked out. Synthetic patches improved point F1 over human labels alone in [DIGMAPPER](https://arxiv.org/html/2506.16006v1). [Jiao et al. 2022](https://doi.org/10.1016/j.jag.2022.102980) used the same idea for roads.
3. **For many map styles, use the legend as the query.** Legend-prompted detection lets one model handle symbols it has not been trained on ([Saxton 2024](https://doi.org/10.3390/geosciences14110305), [Lin F. 2023](https://doi.org/10.1145/3589132.3625659)). Expect weaker results on rare symbols.
4. **Label smartly.** Click approximate centres, then snap them with template matching. This is how YOLSO built 22,882 point labels ([paper](https://eprints.whiterose.ac.uk/id/eprint/198859/)).
5. **Get geographic coordinates from georeferenced sheets.** Run detection on georeferenced GeoTIFFs, or keep the tile offset and apply the sheet's transform to the pixel centre (as mapKurator does for text, [arXiv](https://arxiv.org/html/2306.17059v2)).
6. **Benchmarks:** CaSiDD for generic signs. AI4CMA point features (1-pixel point rasters, scored by distance-based F1 per the [challenge PDF](https://criticalminerals.darpa.mil/Files/Map_Feature_Extraction_Challenge_Details.pdf)).

### 5.2 Area / polygon and line extraction
1. **Baseline: a U-Net on tiles.** With enough labels, a plain U-Net is still hard to beat. It beat MapSAM with full data ([MapSAM](https://arxiv.org/html/2411.06971v1)) and beat transformers on the Paris benchmark ([Chen 2024](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0298217)). Kenya roads used a U-Net/ResNet34 at national scale ([Kramm 2025](https://doi.org/10.1038/s41597-025-05442-6)).
2. **With few labels, reach for:**
   - MapSAM-style SAM fine-tuning ([Xia 2025](https://arxiv.org/abs/2411.06971)).
   - Contrastive pre-training across map editions ([Xia 2023](https://doi.org/10.1145/3615886.3627738)).
   - Pseudo-labels from neighbouring editions ([Yuan 2025](https://arxiv.org/abs/2501.01845), [Wu 2023](https://doi.org/10.1016/j.isprsjprs.2023.01.021)).
   - Synthetic "imitation maps" ([Jiao 2022](https://doi.org/10.1016/j.jag.2022.102980)).
3. **For coarse national coverage, patch classification may be enough** ([MapReader](https://github.com/maps-as-data/MapReader)).
4. **For clean polygons, plan a vectorization stage.** Use edge detection + watershed or closed-shape extraction, and measure with panoptic quality. Start from the [soduco benchmark code](https://github.com/soduco/Benchmark_historical_map_vectorization).
5. **For lines:** segment, skeletonize, vectorize, then classify by symbol style ([Mühlematter 2024](https://arxiv.org/abs/2410.02250)). If a modern vector network exists, Uhl's "verify the modern road on the old map" approach is cheap and accurate ([Uhl 2022](https://doi.org/10.1016/j.compenvurbsys.2022.101794)).

### 5.3 OCR / text spotting
1. **Start with a pretrained map spotter rather than generic OCR:**
   - mapKurator + PALETTE ([GitHub](https://github.com/knowledge-computing/mapkurator-system), [PALETTE](https://github.com/kartta-foundation/mapkurator-palette-doc)) gives tiling, merging, georeferenced GeoJSON output and OSM linking out of the box.
   - Alternatively, the MapText 2024/25 winning DNTextSpotter pipeline ([MapTextPipeline](https://github.com/yyyyyxie/MapTextPipeline)), which has released Rumsey-fine-tuned weights.
   - MapReader also bundles a text-spotting pipeline ([README](https://github.com/maps-as-data/MapReader)).
2. **Fine-tune on your own map style.** Generic models drop sharply on new styles: the 2024 Rumsey winner fell from PDQ 76.1 to 42.3 on French handwritten registers ([MapText 2024](https://weinman.cs.grinnell.edu/pubs/li24icdar.pdf)). Use SynthMap+ or the French synthetic generator to create style-matched synthetic data ([Zenodo 14480731](https://zenodo.org/records/14480731), [generator](https://doi.org/10.5281/zenodo.15498600)).
3. **Evaluate with the MapText protocol and code** ([GitHub](https://github.com/icdar-maptext/evaluation)) on the Rumsey test set, so your numbers compare with published ones. Note that the 2025 metrics differ from the 2024 ones.
4. **Treat linking as its own step.** Use LIGHT ([code](https://github.com/knowledge-computing/multimodal-text-linking)) or a simple MST heuristic ([Olson 2024](https://arxiv.org/abs/2410.15586)) to join multi-word names.
5. **Post-correct with a gazetteer** (OSM or historical gazetteers), as mapKurator does. The same geocoded names can also drive georeferencing ([Milleville 2022](https://doi.org/10.3390/ijgi11070387), [Zou 2025](https://infoscience.epfl.ch/handle/20.500.14299/249929)).
6. **Licensing check:** the Rumsey MapText annotations are **non-commercial** (CC BY-NC-SA 3.0). SynthMap+ (CC BY 4.0) and IGN 2025 (CC BY-SA 4.0) are more permissive.

### 5.4 Glue: georeferencing and legend parsing
- If sheets have printed corner coordinates, read them with OCR or an LLM ([Tyagi & Dubey 2026](https://doi.org/10.1007/978-3-032-08511-5_8); DIGMAPPER).
- Otherwise, geocode the recognized place names ([Milleville 2022](https://doi.org/10.3390/ijgi11070387)), or match against already-georeferenced maps ([Vaienti 2025](https://doi.org/10.1080/15230406.2025.2566789)).
- For legend-driven pipelines, LayoutLMv3 + few-shot GPT-4o reached 88% F1 on legend items ([Kirsanova 2025](https://arxiv.org/abs/2510.08385)).

### 5.5 Gaps to be aware of
- There is no large, multi-series, *class-labelled* point-symbol benchmark for topographic glyphs (churches, wells, mines, triangulation points). CaSiDD is the nearest, and it is mostly class-agnostic.
- Few papers report results directly in geographic units (metres). Most report pixel IoU or F1.
- Many promising 2025–26 works are still preprints (A7, A8, A9, L5, T7, E2, E3, P6).

---

## 6. References

1. Vassányi, G., Gede, M. (2021). Automatic vectorization of point symbols on archive maps using deep convolutional neural network. *Proc. ICA* 4:109. https://doi.org/10.5194/ica-proc-4-109-2021
2. Huang, W. et al. (2023). Leveraging Deep Convolutional Neural Network for Point Symbol Recognition in Scanned Topographic Maps. *ISPRS IJGI* 12(3):128. https://doi.org/10.3390/ijgi12030128
3. Smith, W.A.P., Pillatt, T. (2023). You Only Look for a Symbol Once: An Object Detector for Symbols and Regions in Documents. ICDAR 2023, LNCS. https://doi.org/10.1007/978-3-031-41734-4_14 (accepted version: https://eprints.whiterose.ac.uk/id/eprint/198859/)
4. Saxton, A. et al. (2024). Accurate Feature Extraction from Historical Geologic Maps Using Open-Set Segmentation and Detection. *Geosciences* 14(11):305. https://doi.org/10.3390/geosciences14110305
5. Pai, P.-L. et al. (2025). Application of deep learning for symbol detection on historical maps to explore spatiotemporal changes in the regional tea industry of early 20th-century Taiwan. *Digital Scholarship in the Humanities*. https://doi.org/10.1093/llc/fqaf099
6. Petitpierre, R. (2026). Automated Detection and Encoding of Cartographic Signs in Historical Maps. arXiv:2610.13224. https://arxiv.org/abs/2610.13224
7. Lin, F. et al. (2023). Exploiting Polygon Metadata to Understand Raster Maps – Accurate Polygonal Feature Extraction. ACM SIGSPATIAL 2023. https://doi.org/10.1145/3589132.3625659
8. Wu, S., Heitzler, M., Hurni, L. (2022). Leveraging uncertainty estimation and spatial pyramid pooling for extracting hydrological features from scanned historical topographic maps. *GIScience & Remote Sensing* 59(1). https://doi.org/10.1080/15481603.2021.2023840
9. Wu, S., Schindler, K., Heitzler, M., Hurni, L. (2023). Domain adaptation in segmenting historical maps: A weakly supervised approach through spatial co-occurrence. *ISPRS J. Photogramm. Remote Sens.* 197:199–211. https://doi.org/10.1016/j.isprsjprs.2023.01.021
10. Ståhl, N., Weimann, L. (2022). Identifying wetland areas in historical maps using deep convolutional neural networks. *Ecological Informatics* 68:101557. https://doi.org/10.1016/j.ecoinf.2022.101557
11. Lin, Yue et al. (2023). Creating building-level, three-dimensional digital models of historic urban neighborhoods from Sanborn Fire Insurance maps using machine learning. *PLOS ONE* 18(6):e0286340. https://doi.org/10.1371/journal.pone.0286340
12. Xia, X. et al. (2025). MapSAM: adapting segment anything model for automated feature detection in historical maps. *GIScience & Remote Sensing*. https://doi.org/10.1080/15481603.2025.2494883 (arXiv:2411.06971)
13. Yuan, Y., Thiemann, F., Sester, M. (2025). Semantic Segmentation for Sequential Historical Maps by Learning from Only One Map. arXiv:2501.01845. https://arxiv.org/abs/2501.01845
14. Yuan, Y., Sester, M. (2025). Leveraging LLMs and attention-mechanism for automatic annotation of historical maps. arXiv:2504.11050. https://arxiv.org/abs/2504.11050
15. Rabehi, W., Le Texier, M., Lemoy, R. (2025). Mapping Historic Urban Footprints in France: Balancing Quality, Scalability and AI Techniques. arXiv:2510.02097. https://arxiv.org/abs/2510.02097
16. Hosseini, K., Wilson, D.C.S., Beelen, K., McDonough, K. (2022). MapReader: A Computer Vision Pipeline for the Semantic Exploration of Maps at Scale. GeoHumanities '22. https://doi.org/10.1145/3557919.3565812 (arXiv:2111.15592; software: https://doi.org/10.21105/joss.06434)
17. Uhl, J.H., Leyk, S., Chiang, Y.-Y., Knoblock, C.A. (2022). Towards the automated large-scale reconstruction of past road networks from historical maps. *CEUS* 94:101794. https://doi.org/10.1016/j.compenvurbsys.2022.101794
18. Jiao, C., Heitzler, M., Hurni, L. (2022). A fast and effective deep learning approach for road extraction from historical maps by automatically generating training data with symbol reconstruction. *JAG* 113:102980. https://doi.org/10.1016/j.jag.2022.102980
19. Jiao, C., Heitzler, M., Hurni, L. (2024). A novel framework for road vectorization and classification from historical maps based on deep learning and symbol painting. *CEUS* 108:102060. https://doi.org/10.1016/j.compenvurbsys.2023.102060
20. Xia, X., Jiao, C., Hurni, L. (2023). Contrastive Pretraining for Railway Detection: Unveiling Historical Maps with Transformers. GeoAI '23. https://doi.org/10.1145/3615886.3627738
21. Mühlematter, D.J. et al. (2024). Probabilistic road classification in historical maps using synthetic data and deep learning. arXiv:2410.02250. https://arxiv.org/abs/2410.02250
22. Kramm, T. et al. (2025). Deep learning-based extraction of Kenya's historical road network from topographic maps. *Scientific Data* 12:1149. https://doi.org/10.1038/s41597-025-05442-6
23. Li, Z. et al. (2024). ICDAR 2024 Competition on Historical Map Text Detection, Recognition, and Linking. ICDAR 2024, LNCS. https://doi.org/10.1007/978-3-031-70552-6_22
24. Lin, Y. et al. (2025). ICDAR 2025 Competition on Historical Map Text Detection, Recognition, and Linking. ICDAR 2025, LNCS 16027. https://doi.org/10.1007/978-3-032-04630-7_33
25. Lin, Y., Chiang, Y.-Y. (2024). Hyper-Local Deformable Transformers for Text Spotting on Historical Maps. KDD 2024. https://doi.org/10.1145/3637528.3671589 (arXiv:2506.15010)
26. Kim, J. et al. (2023). The mapKurator System: A Complete Pipeline for Extracting and Linking Text from Historical Maps. ACM SIGSPATIAL 2023 (demo). https://arxiv.org/abs/2306.17059
27. Lin, Y., Olson, R., Wu, J., Chiang, Y.-Y., Weinman, J. (2025). LIGHT: Multi-Modal Text Linking on Historical Maps. ICDAR 2025, LNCS. https://doi.org/10.1007/978-3-032-04617-8_4 (arXiv:2506.22589)
28. Olson, R., Kim, J., Chiang, Y.-Y. (2024). Automatic Search of Multiword Place Names on Historical Maps. GeoSearch '24. https://doi.org/10.1145/3681769.3698577 (arXiv:2410.15586)
29. Zou, M. et al. (2025). Recognizing and Sequencing Multi-word Texts in Maps Using an Attentive Pointer. Research Square preprint. https://doi.org/10.21203/rs.3.rs-6330456/v1
30. Milleville, K., Verstockt, S., Van de Weghe, N. (2022). Automatic Georeferencing of Topographic Raster Maps. *ISPRS IJGI* 11(7):387. https://doi.org/10.3390/ijgi11070387
31. Vaienti, B., di Lenardo, I., Kaplan, F. (2025). Georeferencing historical maps using local feature matching and Delaunay consistency. *Cartography and Geographic Information Science*. https://doi.org/10.1080/15230406.2025.2566789
32. Tyagi, Dubey (2026). Automated Georeferencing of Topographic Maps via OCR and In-Context Multimodal LLM Reasoning. CCIS, Springer. https://doi.org/10.1007/978-3-032-08511-5_8
33. Chen, Y. et al. (2024). Automatic vectorization of historical maps: A benchmark. *PLOS ONE* 19(2):e0298217. https://doi.org/10.1371/journal.pone.0298217
34. Duan, W. et al. (2025). DIGMAPPER: A Modular System for Automated Geologic Map Digitization. arXiv:2506.16006. https://arxiv.org/abs/2506.16006
35. Kirsanova, S., Chiang, Y.-Y., Duan, W. (2025). Detecting Legend Items on Historical Maps Using GPT-4o with In-Context Learning. arXiv:2510.08385. https://arxiv.org/abs/2510.08385

**Supporting sources (not counted as papers):**
- DNTextSpotter, ACM MM 2024: https://arxiv.org/abs/2408.00355
- DARPA Map Feature Extraction Challenge details: https://criticalminerals.darpa.mil/Files/Map_Feature_Extraction_Challenge_Details.pdf
- USGS AI4CMA data release: https://doi.org/10.5066/P9FXSPT1
- Strabo (background, pre-window): https://github.com/spatial-computing/strabo-text-recognition
- SynthMap (GeoAI '21, pre-window): https://arxiv.org/abs/2112.06104
- MapText evaluation code: https://github.com/icdar-maptext/evaluation
- MapText Zenodo community: https://zenodo.org/communities/icdar-maptext

**Excluded for scope or date:**
- BCE-Net (arXiv:2304.07076) mainly uses up-to-date remote-sensing imagery, so it is out of scope.
- ICDAR 2021 MapSeg, Luft et al. 2021 (content-based georeferencing, *Trans. GIS*, Aug 2021) and the SynthMap GeoAI '21 paper are all before 2021-11-19.
