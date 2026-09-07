# 改进方案 Round 1（针对豆包评审 + 自检）

日期: 2026-08-30
输入: `docs/评审记录_round1.md`、R0 网搜结论（VTON SOTA 对比、人脸一致性方案、皮肤真实感、CodeFormer/SUPIR、Qwen 官方参数）

## 总体判断

V6 的"SDXL 局部重绘 + 真实照片基底"路线存在结构性缺陷，不适合继续打磨参数：
1. **SDXL inpaint 大遮罩 denoise 1.0** 等于重新生成，人脸/手/服装结构必然高概率崩坏（评审中全部"严重"项都源于此）
2. **跨人种身份转换**超出 IPAdapter FaceID 能力边界——5 张不同人种基底照注定无法统一为同一亚洲模特
3. 每个案例都要手工标定遮罩多边形，不可扩展，且大遮罩边缘晕影/残贴反复出现

**Round 1 决策：主力管线切换为 Qwen-Image-Edit-2511 指令编辑（官方 fp8mixed 权重），SDXL 管线退役为对照。**

## 问题 → 根因 → 解法

### 1. 换装主图人脸/颈肩/手部崩坏（P1/P2）【严重】
- 根因: SDXL 局部重绘在人脸+颈肩+服装大区域重绘，结构一致性失控；4x 超分进一步放大伪影
- 解法: Qwen-Image-Edit-2511 双图指令换装（image1=模特、image2=裙装平铺/紧裁图）。2511 官方发布重点即"identity preservation + try-on"；脸部/姿态像素级保持是指令编辑模型的原生行为，不再依赖遮罩
- 参数（官方模板）: steps 20-40, CFG 4.0, euler/simple, ModelSamplingAuraFlow shift 3.1, CFGNorm; 可选 Lightning 4 步 LoRA

### 2. 场景重绘身份丢失（P3/P4）【致命】
- 根因: 全幅遮罩 + denoise 1.0 = 无条件重新生成人物；SDXL 管线场景 case 根本没接人脸保持
- 解法: Qwen-Edit 指令"keep the woman unchanged, replace the background with …"，人物保真是默认行为；地中海光影、街拍背景用单图指令编辑
- 补充: 同一模特+同一裙款跨场景一致性由"先换装、后换景"的链式管线保证（换装输出作为场景输入）

### 3. 姿态组六个不同人（P5/P6）【致命】
- 根因: V6 基底照本身是 5 个不同人种模特；FaceID 无法跨人种换脸且不崩
- 解法: Qwen-Edit-2511 多图姿态迁移：image1=锚模特（波点裙正脸照）、image2=姿态参考照 → "the same woman from image 1, same dress, now standing in the pose from image 2"。姿态参考给构图与肢体真实感，锚照给身份
- 保底: 若个别姿态身份漂移，用 insightface（已装 antelopev2/buffalo_l）做人脸相似度初筛 + ReActor 类后替换兜底
- 宣称修正: "六位模特"改为"同一模特六姿态"；若个别姿态实在无法达标则换姿态参考图重生成，不放崩图

### 4. 视频帧间崩坏（P9）【严重】
- 根因: 上游换装静图本身崩坏；Wan 2.2 大幅走秀动作超出 5B 模型能力
- 解法: 用修复后的换装图重新 I2V；动作改为小幅度（缓步/转身/裙摆摆动）；保留 5s 时长但在文案如实说明为"动作预览"而非成片级走秀

### 5. 光板净化涂抹感（P7）【中等】
- 根因: cv2 环带中位色填充 + SDXL 低强度精修在衣领/袖口褶皱处产生平涂抹与形变
- 解法: Qwen-Edit 指令净化（"remove the print on the t-shirt, keep fabric texture and folds"），无遮罩、全局光影一致；对比保留前后图

### 6. P8 评测页放业务不可用失败案例（新发现）【严重】
- 解法: 评测页重做——对照组改为"SDXL 遮罩重绘 vs Qwen-Edit-2511"的成功样例；CLIP-T/CLIP-I 指标附样例图对应；如实写明旧管线失败原因（这是能力证明而不是减分项）

### 7. 文案与实际能力矛盾（贯穿 P1-P6）【严重】
- 解法: 全部文案如实化——删掉"高度保持/逐片锁定"等无法兑现表述；改为描述真实管线（指令编辑+身份保持+人工质检）、量化指标附图、已知限制与质检流程

### 8. P10 良品率自相矛盾 / P11 口号空洞（新发现）【严重】
- 解法: P10 重写为"质检分级展示"：直出可用/修复后可用/淘汰三类真实样本+流程图（生成→检测→修复→复检）；P11 封底改为收敛的一句话定位+代表作三图+明确"本人产出范围"

### 9. 超分链路未脚本化（工程债）
- 解法: 新增 `upscale_api.py`，用 ComfyUI API 固化 4x-UltraSharp 放大（LoadImage→UpscaleModelLoader→ImageScaleBy→SaveImage），纳入 package 流程，保证可复现

## Round 1 生成清单

| 页面 | 动作 | 管线 |
|---|---|---|
| P1 封面主图 | 重做换装（波点裙→花卉裙） | Qwen-Edit-2511 |
| P2 换装页 | 重做 + BEFORE/AFTER | Qwen-Edit-2511 |
| P3/P4 场景 ×2 | 换装图→背景替换 | Qwen-Edit-2511 链式 |
| P5 姿态宫格 | 锚模特×姿态参考 重生成 6 姿态 | Qwen-Edit-2511 多图 |
| P6 精选 | 从 P5 中选 3 张重排 | 同上 |
| P7 光板 | 指令去印花 ×3 | Qwen-Edit-2511 |
| P8 评测 | SDXL vs Qwen-Edit 重测重写 | 双管线+eval_metrics |
| P9 视频 | 新换装图重跑 Wan 2.2 小动作 | Wan 2.2 |
| P10/P11 | 文案与结构重写 | 内容 |
| 全部图 | 脚本化 4x 超分 | upscale_api.py |

## 依据来源
- [Qwen-Image-Edit-2511 官方博客](https://qwen.ai/blog?id=qwen-image-edit-2511)：身份保持/多人一致性/姿态迁移
- [ComfyUI 官方 2511 教程](https://docs.comfy.org/tutorials/image/qwen/qwen-image-edit-2511) 与本地模板 `image_qwen_image_edit_2511_lora_inflation.json`（参数: 20 步 cfg 4 / 40 步更优 / Lightning 4 步 cfg 1）
- [FASHN VTON 四模型对比](https://fashn.ai/blog/comparing-the-top-4-open-source-virtual-try-on-viton-models)、[FitDiT 论文](https://arxiv.org/html/2411.10499v1)：专用 VTON 与指令编辑路线的取舍
- [facerestore_cf（CodeFormer/GFPGAN）](https://github.com/mav-rik/facerestore_cf)：兜底面部修复（fidelity 0.5-0.8）
- [SUPIR 讨论](https://www.reddit.com/r/comfyui/comments/1j8i0yv/what_is_the_best_upscaler_currently/)：16GB 可跑但慢，本轮先用 4x-UltraSharp 脚本化
- 豆包评审修改方向四条（精修/身份一致/文案如实/不放原始生成图）
