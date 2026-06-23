from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1600, 900
BG, GREEN, LIGHT, GRID = "#f7f6f4", "#3e7b61", "#c9d9cd", "#27362f"
img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

REG = r"C:\Windows\Fonts\malgun.ttf"
BOLD = r"C:\Windows\Fonts\malgunbd.ttf"

def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else REG, size)

def centered(text, box, size, fill="#17221d", bold=False):
    x1, y1, x2, y2 = box
    f = font(size, bold)
    b = d.textbbox((0, 0), text, font=f)
    d.text(((x1+x2-b[2])/2, (y1+y2-b[3])/2-2), text, font=f, fill=fill)

def lines(text, x, y, width, size=16, gap=7, bold_first=False, fill="#202722"):
    f, fb = font(size), font(size, True)
    yy = y
    for i, raw in enumerate(text.split("\n")):
        use = fb if bold_first and i == 0 else f
        words, row = raw.split(" "), ""
        for word in words:
            candidate = (row + " " + word).strip()
            if d.textlength(candidate, font=use) > width and row:
                d.text((x, yy), row, font=use, fill=fill)
                yy += size + gap
                row = word
            else:
                row = candidate
        d.text((x, yy), row, font=use, fill=fill)
        yy += size + gap
    return yy

def rect(box, fill, outline=GRID, radius=0, width=1):
    if radius:
        d.rounded_rectangle(box, radius, fill=fill, outline=outline, width=width)
    else:
        d.rectangle(box, fill=fill, outline=outline, width=width)

def arrow(x1, y, x2):
    d.line((x1, y, x2-10, y), fill=GREEN, width=4)
    d.polygon([(x2-10,y-7),(x2,y),(x2-10,y+7)], fill=GREEN)

# Title
d.text((38, 10), "T.3 아키텍처", font=font(44, True), fill="#294f40")
d.line((38, 76, 1562, 76), fill="#2d3632", width=2)

# Geometry
xs = [24, 96, 336, 538, 740, 942, 1144, 1346, 1576]
for box, label in [((24,104,96,162),""),((96,104,336,162),"데이터 구성"),((336,104,1346,162),"T2 MRI 전처리 파이프라인"),((1346,104,1576,162),"산출물 및 QC")]:
    rect(box, GREEN)
    if label: centered(label, box, 27, "white", True)

headers = ["코호트 선정","DICOM → NIfTI","뇌 추출 (BET)","N4 보정","MNI152 정합","정규화 · 리사이즈","로그 · 시각화"]
for i, label in enumerate(headers):
    box=(xs[i+1],162,xs[i+2],208); rect(box,LIGHT); centered(label,box,19,bold=True)
rect((24,162,96,208),LIGHT)

rows=[(208,460,"결과"),(460,698,"서비스"),(698,872,"기술")]
for y1,y2,label in rows:
    rect((24,y1,96,y2),"#d9d9d9"); rect((96,y1,1576,y2),"white")
    centered(label,(24,y1,96,y2),20,bold=True)
for x in xs[2:-1]: d.line((x,208,x,872),fill=GRID,width=1)

# Cohort result
rect((114,225,318,373),"#f0f5f2","#aac0b2",8)
centered("최종 303명 / 303영상",(114,230,318,263),19,"#294f40",True)
bars=[("Control",110,"#4e8e72"),("Prodromal",58,"#8fba9f"),("PD",135,"#2f684f")]
for j,(name,n,color) in enumerate(bars):
    y=276+j*34; d.text((126,y),name,font=font(14),fill="#3e4a44")
    d.rounded_rectangle((205,y,205+int(n*.76),y+16),3,fill=color)
    d.text((292,y),str(n),font=font(14),fill="#3e4a44")
centered("피험자당 대표 T2 영상 1개",(110,388,322,414),14,"#3e4a44")
centered("MRI · Original · FLAIR 제외",(110,414,322,440),14,"#3e4a44")

# Pipeline result cards
cards=[(356,"3D NIfTI","재지향 · Echo 선택"),(558,"비뇌 조직 제거","두개골 제거 영상"),(760,"Bias field 보정","명암 불균일 완화"),(962,"표준 공간 정렬","12-DOF 선형 정합"),(1164,"56 × 56 × 56","z-score · clip [-5, 5]")]
for idx,(x,title,sub) in enumerate(cards):
    rect((x,232,x+162,378),"#edf3ef","#9cb5a6",10)
    cx=x+81
    if idx==0:
        d.rectangle((cx-45,258,cx+40,342),fill="white",outline="#4d7664",width=2); d.polygon([(cx+15,258),(cx+40,283),(cx+15,283)],fill="#dce8e1")
    elif idx==1:
        d.ellipse((cx-45,248,cx+45,356),fill="#303633"); d.ellipse((cx-31,259,cx+31,346),fill="#cad3ce")
        d.line((cx,264,cx,340),fill="white",width=2)
    elif idx==2:
        d.ellipse((cx-60,258,cx+2,342),fill="#737b77"); d.ellipse((cx-2,258,cx+60,342),fill="#b7c5bd")
        d.line((cx,252,cx,348),fill=GREEN,width=3)
    elif idx==3:
        for q in range(-45,46,18): d.line((cx+q,252,cx+q,350),fill="#a8b8b0")
        for q in range(-45,46,18): d.line((cx-55,301+q,cx+55,301+q),fill="#a8b8b0")
        d.ellipse((cx-36,257,cx+36,349),fill="#47755f")
    else:
        d.rectangle((cx-52,258,cx+52,346),outline="#b3c1ba")
        d.line([(cx-48,335),(cx-30,320),(cx-18,278),(cx,307),(cx+17,335),(cx+30,281),(cx+49,265)],fill=GREEN,width=4)
    centered(title,(x,385,x+162,414),18,"#294f40",True); centered(sub,(x,414,x+162,442),14,"#3e4a44")

# QC card
rect((1366,232,1556,378),"#26332d","#26332d",10)
for k,t in enumerate(["[303/303] complete","status: ok / failed","timing: stage/sec","QC: 3-plane montage"]):
    d.text((1381,247+k*29),t,font=ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf",15),fill="#d6e6dc")
centered("추적 가능한 산출물",(1360,385,1562,414),18,"#294f40",True); centered("단계별 NIfTI · CSV 로그",(1360,414,1562,442),14,"#3e4a44")
for a,b in [(318,356),(518,558),(720,760),(922,962),(1124,1164),(1326,1366)]: arrow(a+2,305,b-8)

# Service row
service=[
"1. 선정 기준\n• MRI / Original / T2 계열\n• FLAIR, T2*, REPEAT, MPR 제외\n2. 중복 제어\n• Subject·Image ID 중복 검증\n• BL 및 표준 촬영 우선",
"원천 영상 변환\n• DICOM 폴더 인벤토리\n• 다중 Echo: 최대 TE 선택\n• 4D 결과: 마지막 볼륨\n• 최대 3D 볼륨 채택",
"Brain extraction\n• 뇌 실질 영역 분리\n• 배경·두개골 제거\n• 다음 단계 입력 생성",
"Intensity correction\n• 저주파 편향장 추정\n• 공간적 명암 편차 보정\n• 조직 대비 안정화",
"Spatial registration\n• MNI152 1 mm template\n• 12 자유도 affine 정합\n• 피험자 간 공간 표준화",
"Model-ready volume\n• 비영점 voxel z-score\n• 범위 [-5, 5] clipping\n• 56³ voxel 크기 통일",
"품질·실행 관리\n• 샘플별 성공/실패 기록\n• 단계별·전체 처리시간\n• 3-plane 시각화\n• Before/After 비교"
]
for i,t in enumerate(service): lines(t,xs[i+1]+16,482,xs[i+2]-xs[i+1]-30,15,8,True)

# Technology row
tech=[
"데이터/검증\nPython · CSV · XLSX\n메타데이터 교차검증\nControl=0 · Prodromal=1 · PD=2",
"dicom2nifti\npydicom · nibabel\nreorient · gzip NIfTI",
"FSL BET\nSkull stripping\nWSL / Linux",
"ANTs N4\nN4BiasFieldCorrection\nBias correction",
"FSL FLIRT\nMNI152_T1_1mm_brain\n12-DOF affine",
"NumPy · nibabel\nz-score normalization\n3D resize (56³)",
"병렬 처리 및 QC\nProcessPoolExecutor (4 workers)\nMatplotlib · preprocessing_log.csv\n단계 폴더 01–06 · 재시작 지원"
]
for i,t in enumerate(tech): lines(t,xs[i+1]+16,722,xs[i+2]-xs[i+1]-30,14,9,True)

d.text((1175,878),"PPMI T2 MRI · 303 unique subjects · Paper-aligned preprocessing",font=font(13),fill="#56645d")

# Replace schematic placeholders with actual project images.
VIS = r"E:\ppmi_dti\preprocessed\t2_paper_303\visualization\sub-3008_I366281"
SUMMARY = r"C:\Users\asia\Documents\파이널\outputs\t2_303_unique_subjects\summary_preview.png"

def paste_contain(path, box, crop=None, bg="white"):
    source = Image.open(path).convert("RGB")
    if crop == "axial":
        sw, sh = source.size
        source = source.crop((int(sw * .72), int(sh * .18), int(sw * .995), int(sh * .98)))
    elif crop == "summary":
        sw, sh = source.size
        source = source.crop((int(sw * .03), int(sh * .04), int(sw * .68), int(sh * .60)))
    x1, y1, x2, y2 = box
    frame = Image.new("RGB", (x2-x1, y2-y1), bg)
    fitted = ImageOps.contain(source, frame.size, Image.Resampling.LANCZOS)
    frame.paste(fitted, ((frame.width-fitted.width)//2, (frame.height-fitted.height)//2))
    img.paste(frame, (x1, y1))
    d.rectangle(box, outline="#9cb5a6", width=1)

paste_contain(SUMMARY, (116, 234, 316, 371), "summary")
actual_stage_images = [
    (rf"{VIS}\01_raw.png", (358, 234, 516, 376), "axial", "black"),
    (rf"{VIS}\02_bet_after.png", (560, 234, 718, 376), "axial", "black"),
    (rf"{VIS}\03_n4_after.png", (762, 234, 920, 376), "axial", "black"),
    (rf"{VIS}\04_mni152_after.png", (964, 234, 1122, 376), "axial", "black"),
    (rf"{VIS}\06_resized_after.png", (1166, 234, 1324, 376), "axial", "#7f7f7f"),
    (rf"{VIS}\PPT_full_pipeline_overview.png", (1368, 234, 1554, 376), None, "white"),
]
for path, box, crop, bg in actual_stage_images:
    paste_contain(path, box, crop, bg)

img.save("t2_preprocessing_architecture.png",dpi=(150,150))
