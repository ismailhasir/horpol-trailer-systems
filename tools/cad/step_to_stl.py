# Üretici STEP dosyasını kabuk (shell) başına STL'lere ayırır (FreeCAD; Blender lamba betiği bunları okur).
# Çalıştırma (depo kökünden):
#   STEP_IN="<...>/LZD 3194_H101_AMP_4SS.STEP" STEP_OUT=tools/blender/cad/lzd3194 \
#     "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" tools/cad/step_to_stl.py
# Çıktı: p000.stl … pNNN.stl (milimetre, CAD ekseni) + parts.json (yüz/üçgen sayısı, sınır kutusu).
# STEP ve STL'ler repoya girmez (büyük, üretici verisi): tools/blender/cad/ .gitignore'da.
import json
import os

import MeshPart
import Part

src = os.environ['STEP_IN']
out = os.environ['STEP_OUT']
defl = float(os.environ.get('STEP_DEFL', '0.05'))  # doğrusal sapma, mm
os.makedirs(out, exist_ok=True)
shape = Part.Shape()
shape.read(src)
print('SOLIDS', len(shape.Solids), 'SHELLS', len(shape.Shells), 'FACES', len(shape.Faces))
info = []
for i, s in enumerate(shape.Shells):
    b = s.BoundBox
    m = MeshPart.meshFromShape(Shape=s, LinearDeflection=defl, AngularDeflection=0.35, Relative=False)
    m.write(os.path.join(out, f'p{i:03d}.stl'))
    info.append({'i': i, 'faces': len(s.Faces), 'tris': m.CountFacets,
                 'bb': [round(v, 2) for v in (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax)]})
json.dump({'source': os.path.basename(src), 'deflection_mm': defl, 'parts': info}, open(os.path.join(out, 'parts.json'), 'w'), indent=1)
print('DONE', len(info), 'tris', sum(p['tris'] for p in info))
