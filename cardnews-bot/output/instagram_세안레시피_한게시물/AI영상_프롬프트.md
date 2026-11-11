# 사람이 움직이는 릴스 만들기 — AI 영상 프롬프트

사진 속 사람을 실제로 움직이게 하려면 **온라인 AI 영상 서비스**(사진 → 영상)를 써야 해요.
이 PC(내장 그래픽, 메모리 8GB)로는 만들 수 없어요.

## 순서

1. AI 영상 서비스에 가입하고 로그인 (직접 해 주세요)
   - 예: Runway, Kling AI, Luma Dream Machine, Pika, Google Veo 등
   - 대부분 **무료 크레딧이 조금** 있고, 더 쓰려면 유료예요. 가격은 각 사이트에서 확인하세요.
   - 서비스 **이용 약관에서 상업적 사용(인스타 게시) 가능 여부**도 확인하세요.
2. 아래 표의 **사진**을 올리고, **프롬프트**를 그대로 붙여넣기
   - 설정: **세로 또는 원본 비율**, 길이 **5초**, 움직임 강도는 **낮게(subtle)**
3. 만들어진 영상을 받아서 **저장 이름**대로 바꿔 아래 폴더에 넣기
   - `assets/people/세안_AI영상/` (예: `01.mp4`, `02.mp4` …)
4. Claude에게 "AI 영상으로 릴스 만들어 줘"라고 말하기
   - 일부만 넣어도 돼요. 영상이 없는 장면은 지금처럼 사진 + 움직임 효과로 들어가요.

## 장면별 프롬프트

모든 프롬프트 끝에 공통 문장을 붙이면 결과가 더 안정적이에요:
`Keep her face and identity exactly the same. Natural, slow, realistic motion. No text, no logos, no change to skin.`

| 저장 이름 | 올릴 사진 (`assets/people/세안/`) | 프롬프트 (영어로 붙여넣기) | 무슨 장면 |
|---|---|---|---|
| `01.mp4` | `m3x.jpg` | A woman in a bathroom rubs her foamy face firmly with both hands, frowning slightly, small circular motions. Camera static. | 박박 문지르기 (실수) |
| `02.mp4` | `m2x.jpg` | A woman spreads cleanser directly onto her cheek with her fingers without making foam first, quick strokes. Camera static. | 거품 없이 바로 쓱쓱 (실수) |
| `03.mp4` | `m2o.jpg` | A woman gently whips white foam between her palms, the foam grows fluffy like whipped cream, she smiles softly. Camera slowly pushes in. | 손에서 거품 휘핑 |
| `04.mp4` | `m3o.jpg` | A woman gently rolls her fingertips in small circles on her foamy cheek, relaxed and soft touch. Camera static. | 손끝으로 롤링 |
| `05.mp4` | `step1_apply.webp` | A woman slowly spreads a thick layer of pink cream mask on her cheek with her fingers, calm expression. Camera static. | STEP 1 팩 바르기 |
| `06.mp4` | `pack.jpg` | A woman with a cream mask on her cheek stays still and relaxed, blinks slowly and breathes calmly, waiting. Camera static. | STEP 2 1분 기다리기 |
| `07.mp4` | `m4x.jpg` | A woman leans over a sink and splashes lukewarm water onto her face with cupped hands, water droplets falling. Camera static. | STEP 3 미온수로 헹구기 |
| `08.mp4` | `hair.jpg` | A woman gently rinses along her hairline and under her jaw with wet fingers, turning her head slightly. Camera static. | 헤어라인·턱 밑 헹굼 |
| `09.mp4` | `pat.jpg` | A woman gently pats her face dry with a soft white towel, pressing lightly without rubbing, smiling. Camera static. | STEP 4 톡톡 닦기 |
| `10.mp4` | `foam.jpg` | A woman massages light foam on her cheek with wet fingertips in small circles, morning light. Camera static. | TIP 폼으로 쓰기 |
| `11.mp4` | `whipped_tubes.jpg` | Slow camera push-in over cleanser tubes on a table. The tubes and labels do not change or move. | 마무리 (제품) |

## 꼭 지킬 것

- 인스타에 올릴 때 **"AI 정보" 레이블을 켜 주세요.** 사람이 나오는 실사 느낌의 AI 영상이라 표시가 필요해요.
- AI가 만든 영상에서 **피부가 좋아지는 것처럼 보이는 장면은 쓰지 마세요** (화장품 효과 과장).
- 손가락이 이상하거나 얼굴이 바뀐 영상은 다시 만들거나 그 장면은 사진으로 두세요.
- 11번 제품 영상에서 **상표·글자가 바뀌면 쓰지 마세요.** 그 장면은 사진으로 두는 게 안전해요.
- 사진의 원래 출처와 사용 권한을 먼저 확인하세요.
