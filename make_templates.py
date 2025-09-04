from pathlib import Path

root = Path("data"); root.mkdir(parents=True, exist_ok=True)

materials = """material_id,grade,en_number,category,form,density_kg_per_m3,price_eur_per_kg,price_source,source_url,source_date,scrap_pct,yield_loss_pct,notes
STEEL_S235,S235JR,1.0038,carbon_steel,plate,7850,,,,,0.03,0.02,Common structural
STEEL_S355,S355J2,1.0570,carbon_steel,plate,7850,,,,,0.03,0.02,Structural tougher
SS_304L,304L,1.4307,stainless,plate,8000,,,,,0.05,0.03,Austenitic
SS_316L,316L,1.4404,stainless,plate,8000,,,,,0.05,0.03,Corrosion resistant
SS_Duplex_2205,2205,1.4462,stainless,plate,7800,,,,,0.06,0.03,Duplex
SS_SuperDuplex,Z100,1.4410,stainless,plate,7800,,,,,0.07,0.03,Super Duplex
AL_6082,6082-T6,,aluminium,plate,2700,,,,,0.04,0.03,General purpose
AL_7075,7075-T651,,aluminium,plate,2810,,,,,0.05,0.03,High strength
AL_Cast_AlSi10Mg,AlSi10Mg,,aluminium,casting,2680,,,,,0.06,0.04,Casting alloy
CU_CuETP,Cu-ETP,,copper,bar,8960,,,,,0.03,0.02,Electrical copper
BR_Ms58,CuZn39Pb3,2.0401,brass,bar,8500,,,,,0.04,0.03,Free-cutting brass
TI_Grade5,Ti-6Al-4V,3.7165,titanium,bar,4430,,,,,0.07,0.04,Aerospace
NI_Inconel718,Inconel 718,2.4668,nickel_alloy,bar,8190,,,,,0.08,0.05,High temperature
NI_HastC276,Hastelloy C-276,2.4819,nickel_alloy,plate,8900,,,,,0.08,0.05,Corrosion resistant
CAST_Steel_GS52,GS-52,,cast_steel,casting,7850,,,,,0.06,0.04,Cast steel generic
CAST_Iron_GG25,EN-GJL-250,,cast_iron,casting,7100,,,,,0.06,0.04,Grey cast iron
PLASTIC_POM,POM-C,,plastic,plate,1420,,,,,0.03,0.02,Acetal
PLASTIC_PEEK,PEEK,,plastic,plate,1320,,,,,0.05,0.03,High-performance
"""
(processes := """process_id,name,machine_group,machine_rate_eur_h,labor_rate_eur_h,setup_min,batch_min_qty,run_time_formula,scrap_pct,overhead_pct,margin_pct,notes
CNC_MILL_3AX,3-axis milling,CNC_mill,95,45,30,1,"time_min = (toolpath_mm / feed_mm_min) + (passes * retract_penalty_min)",0.02,0.25,0.10,General 3-axis
CNC_MILL_5AX,5-axis milling,CNC_mill,135,50,40,1,"time_min = (toolpath_mm / feed_mm_min) * k_complexity",0.02,0.25,0.12,Simultaneous 5-axis
CNC_TURN,CNC turning,CNC_lathe,85,45,20,1,"time_min = (cut_len_mm / feed_mm_rev) / rpm * 60",0.02,0.25,0.10,Bar work
LASER_SHEET,Laser cutting,sheet_cut,75,35,10,1,"time_min = (cut_len_mm / cut_speed_mm_min) + pierces * pierce_time_min",0.01,0.20,0.10,Fiber laser
BEND,CNC bending,press_brake,70,35,15,1,"time_min = bends * (0.5 + part_rotate_penalty_min)",0.01,0.20,0.10,Press brake
WELD_MAG,MAG welding,welding,60,40,15,1,"time_min = weld_len_mm / dep_rate_mm_min",0.03,0.25,0.12,Steel MAG
WELD_TIG,TIG welding,welding,65,45,20,1,"time_min = weld_len_mm / dep_rate_mm_min * k_precision",0.03,0.25,0.12,Stainless TIG
GRIND,Surface grinding,grinding,80,40,20,1,"time_min = area_mm2 / mrr_mm3_min / depth_mm",0.02,0.25,0.12,Finish grinding
SAW,Band sawing,cutting,55,30,5,1,"time_min = cut_len_mm / saw_speed_mm_min",0.02,0.20,0.08,Bar/plate cut
HEAT_TREAT,Heat treatment,heat_treat,0,0,0,1,"time_min = 0; cost = lot_flat_eur + mass_kg * kg_rate_eur",0.00,0.15,0.10,External service
BLAST,Bead blasting,finishing,50,35,10,1,"time_min = area_mm2 / throughput_mm2_min",0.01,0.20,0.10,Finish
AM_LPBF,Metal 3D print (LPBF),additive,180,40,60,1,"time_min = volume_cm3 / build_rate_cm3_h * 60",0.05,0.25,0.15,Al/SS/Ti LPBF
CASTING,Casting (foundry),casting,0,0,0,1,"time_min = 0; cost = lot_tooling_eur + mass_kg * kg_cast_rate_eur",0.03,0.20,0.12,External foundry
""")
(bom := """item_no,parent,part_no,description,material_id,qty,uom,length_mm,width_mm,thickness_mm,diameter_mm,height_mm,mass_kg,process_route,tolerance_class,surface_ra_um,heat_treat,notes
10,ROOT,P-0001,Base plate,SS_316L,1,pcs,200,150,12,,,"",LASER_SHEET;BEND;CNC_MILL_3AX,ISO 2768-mK,3.2,,Example
20,ROOT,P-0002,Shaft,SS_Duplex_2205,1,pcs,,,,35,250,,"SAW;CNC_TURN;GRIND",ISO 2768-fH,1.6,,Example
""")
(Path("data/materials_db.csv")).write_text(materials, encoding="utf-8")
(Path("data/processes_db.csv")).write_text(processes, encoding="utf-8")
(Path("data/bom_template.csv")).write_text(bom, encoding="utf-8")
print("Templates geschreven naar ./data/")
