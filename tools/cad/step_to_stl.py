# Üretici STEP dosyasını kabuk (shell) başına STL'lere ayırır (FreeCAD; Blender lamba betiği bunları okur).
# Çalıştırma (depo kökünden):
#   STEP_IN="<...>/LZD 3194_H101_AMP_4SS.STEP" STEP_OUT=tools/blender/cad/lzd3194 \
#     "C:/Program Files/FreeCAD 1.1/bin/freecadcmd.exe" tools/cad/step_to_stl.py
# Çıktı: p000.stl … pNNN.stl (milimetre, CAD ekseni) + parts.json (yüz/üçgen sayısı, sınır kutusu).
# STEP ve STL'ler repoya girmez (büyük, üretici verisi): tools/blender/cad/ .gitignore'da.
import json
import os

import Mesh
import MeshPart
import Part

src = os.environ['STEP_IN']
out = os.environ['STEP_OUT']
defl = float(os.environ.get('STEP_DEFL', '0.05'))  # doğrusal sapma, mm
os.makedirs(out, exist_ok=True)
shape = Part.Shape()
shape.read(src)
print('SOLIDS', len(shape.Solids), 'SHELLS', len(shape.Shells), 'FACES', len(shape.Faces))


def per_face(s):
    """Kabuk bütün olarak üçgenlenemezse (bozuk yüz kabuğun sınır kutusunu geçersiz kılıyor: LTD 2834 kabuk 4) yüz yüz
    üçgenle; üçgenlenemeyen yüzler atlanır ve sayısı yazılır"""
    tris, bad = [], 0
    for f in s.Faces:
        try:
            v, t = f.tessellate(defl)
        except Exception:
            bad += 1
            continue
        if not t:
            bad += 1
        tris += [[tuple(v[a]), tuple(v[b]), tuple(v[c])] for a, b, c in t]
    print('PER_FACE', len(s.Faces), 'faces, skipped', bad)
    return Mesh.Mesh(tris)


info = []
for i, s in enumerate(shape.Shells):
    b = s.BoundBox
    m = MeshPart.meshFromShape(Shape=s, LinearDeflection=defl, AngularDeflection=0.35, Relative=False)
    if m.CountFacets == 0 and s.Faces:
        m = per_face(s)
        b = m.BoundBox
    m.write(os.path.join(out, f'p{i:03d}.stl'))
    info.append({'i': i, 'faces': len(s.Faces), 'tris': m.CountFacets,
                 'bb': [round(v, 2) for v in (b.XMin, b.XMax, b.YMin, b.YMax, b.ZMin, b.ZMax)]})
json.dump({'source': os.path.basename(src), 'deflection_mm': defl, 'parts': info}, open(os.path.join(out, 'parts.json'), 'w'), indent=1)
print('DONE', len(info), 'tris', sum(p['tris'] for p in info))
