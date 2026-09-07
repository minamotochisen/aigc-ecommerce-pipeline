# -*- coding: utf-8 -*-
"""V13: 作品集 HTML 改写 — 04 视频章节 4 页替换旧单页, 封面/封底/页码同步"""
import os

ROOT = r"."
HTML = os.path.join(ROOT, "portfolio_v2.html")

P = "outputs_v2/video_v13/plates/"

NEW = f'''
<!-- P9 04A 视频生成·走秀与姿态 -->
<div class="page">
  <div class="head"><div class="no">04</div><div class="t">AI 视频生成 · 走秀与姿态</div>
    <div class="en">FASHION VIDEO · I</div></div>
  <div class="sub">换装/姿态静图 → <b>Wan 2.2 TI2V 5B 图生视频</b> · 704×1280 竖版 · 24fps · 49 帧（约 2 秒）。首帧全部取自图片管线终选成片——<b>视频与静图共用同一身份锚，图动一体</b>。<br><span style="font-size:8px;color:var(--muted);">如实说明：5B 端侧模型动作幅度保守（重心转移/回眸级），大幅走秀位移为已知能力边界（见 04B 评测页）；胶片条为每 10% 帧位实抽。</span></div>

  <img src="{P}strip_runway_step.jpg" style="width:100%; display:block; border:1px solid var(--line);" alt="">
  <div class="cap"><span>镜头 01 · 走秀迈步（缓步 + 裙摆摆动）</span><span>seed 63011 · 20 步</span></div>
  <div style="height:3mm"></div>
  <img src="{P}strip_walk_street.jpg" style="width:100%; display:block; border:1px solid var(--line);" alt="">
  <div class="cap"><span>镜头 02 · 姿态行走（波点长裙 · 姿态组同源）</span><span>seed 63021 · 20 步</span></div>
  <div style="height:3mm"></div>
  <img src="{P}strip_runway_turn.jpg" style="width:100%; display:block; border:1px solid var(--line);" alt="">
  <div class="cap"><span>镜头 03 · 回眸（头部缓慢转动 + 发丝跟随）</span><span>seed 63032 · 20 步</span></div>

  <div style="height:3.5mm"></div>
  <div style="display:flex; gap:6mm;">
    <div class="card" style="flex:1; padding:8px 10px;">
      <div style="font-size:9.5px; font-weight:700; margin-bottom:1.5mm;">生成链路</div>
      <div style="font-size:8.5px; color:var(--muted); line-height:1.7;">首帧 = 换装管线 2600×3466 终选成片（裁 704×1280，人脸偏移对齐）→ Wan 2.2 TI2V 5B（48 通道 VAE）→ uni_pc · CFG 5 · shift 8 · 20 步 ≈ 3.4 分钟/条（含看门狗重启）。</div>
    </div>
    <div class="card" style="flex:1; padding:8px 10px;">
      <div style="font-size:9.5px; font-weight:700; margin-bottom:1.5mm;">动作设计经验</div>
      <div style="font-size:8.5px; color:var(--muted); line-height:1.7;">文本驱动只能到"重心转移级"动作；<b>自然步态来自行走姿态照首帧</b>（图像先验强于文本驱动）。静止镜头需显式写死"双臂下垂/无手势"——自发手势幻觉是 5B 最大翻车点（详见 04D 审片）。</div>
    </div>
  </div>
  <div class="pagefoot"><span>04 AI 视频生成 · 走秀与姿态</span><span>09</span></div>
</div>

<!-- P10 04B 视频生成·场景/面料/首尾帧转场 -->
<div class="page">
  <div class="head"><div class="no">04</div><div class="t">AI 视频生成 · 场景与转场</div>
    <div class="en">SCENE & TRANSITION · II</div></div>
  <div class="sub">图生视频扩展到<b>场景氛围、面料微距</b>（1280×704 横版），并用 <b>Wan 2.1 FLF2V 14B（fp8）首尾帧控制</b>实现<b>一条视频内完成换装</b>：换装前真实输入作首帧、换装管线成片作尾帧——电商视频化的强卖点形态。</div>

  <img src="{P}strip_pose_twirl.jpg" style="width:100%; display:block; border:1px solid var(--line);" alt="">
  <div class="cap"><span>镜头 04 · 背身回眸（竖版）</span><span>seed 63042</span></div>
  <div style="height:3mm"></div>
  <img src="{P}strip_scene_street.jpg" style="width:100%; display:block; border:1px solid var(--line);" alt="">
  <div class="cap"><span>镜头 05 · 欧洲街拍行走（人物走动 + 发丝飘动 + 跟随镜头）</span><span>seed 63071</span></div>
  <div style="height:3mm"></div>
  <img src="{P}strip_flf.jpg" style="width:100%; display:block; border:1px solid var(--line);" alt="">
  <div class="cap"><span>镜头 06 · <b>首尾帧换装转场</b>（波点裙 → 花卉吊带裙，73 帧中间态由模型生成）</span><span>FLF2V 14B · seed 63101</span></div>

  <div style="height:3.5mm"></div>
  <div style="display:flex; gap:6mm;">
    <div class="card" style="flex:1; padding:8px 10px;">
      <div style="font-size:9.5px; font-weight:700; margin-bottom:1.5mm;">首尾帧对齐是成败关键</div>
      <div style="font-size:8.5px; color:var(--muted); line-height:1.7;">首尾帧人脸纵向偏移需人工对齐（裁片 bias 参数化），差异过大时中间帧"融化"；本例首尾同机位同姿态，过渡稳定。</div>
    </div>
    <div class="card" style="flex:1; padding:8px 10px;">
      <div style="font-size:9.5px; font-weight:700; margin-bottom:1.5mm;">场景/面料镜头</div>
      <div style="font-size:8.5px; color:var(--muted); line-height:1.7;">奶油室内（窗帘摆动+推近）、面料微距（提花布纹流动）随精选视频包交付，并全部进入 reel 混剪——一套静图素材裂变"图 + 视频"双形态。</div>
    </div>
  </div>
  <div class="pagefoot"><span>04 AI 视频生成 · 场景与转场</span><span>10</span></div>
</div>

<!-- P11 04C 视频技术选型与评测 -->
<div class="page">
  <div class="head"><div class="no">04B</div><div class="t">视频生成 · 技术选型与评测</div>
    <div class="en">VIDEO BENCHMARK · III</div></div>
  <div class="sub">三条模型路线同机实测（RTX 4070 Ti SUPER 16GB）：<b>5B 原生 20 步为主力</b>；14B 系列验证端侧可行性。含一次<b>判负实验</b>：TI2V-5B 纯文生视频两个 prompt 均完全跑题（输出与文本无关），证实该模型<b>文本只驱动运动、内容必须图像条件</b>——"文生视频"需 14B T2V 或云端承担。</div>

  <img src="{P}strip_ab_steps.jpg" style="width:100%; display:block; border:1px solid var(--line);" alt="">
  <div class="cap"><span>同 seed 步数 A/B（走秀镜头）：12 步与 20 步纹理接近，20 步更优</span><span>12 步省 26% 机时</span></div>
  <div style="height:3mm"></div>
  <img src="{P}strip_14b_vs_5b.jpg" style="width:100%; display:block; border:1px solid var(--line);" alt="">
  <div class="cap"><span>14B Lightning（lightx2v 4 步蒸馏 LoRA · CFG 1 · shift 5）与 5B 原生对照</span><span>A14B I2V 双专家 fp8</span></div>

  <div style="height:3mm"></div>
  <table class="kv">
    <tr><td class="k">主力 · Wan 2.2 TI2V 5B fp16</td><td class="v">704×1280 / 1280×704 · 49帧 24fps · 20 步 <b>203s/条</b>（12 步 149s）——身份/服装/背景稳定性最好，动作幅度保守</td></tr>
    <tr><td class="k">首尾帧 · Wan 2.1 FLF2V 14B fp8</td><td class="v">1280×720 · 73帧 16fps · 20 步——16GB 卡静态显存下 <b>≈250s/步</b>（20 步约 80 分钟，可用但慢，批产需云端/多卡）</td></tr>
    <tr><td class="k">加速 · I2V A14B + Lightning LoRA</td><td class="v">1280×720 · 81帧 16fps · <b>4 步（2+2 拆段）· CFG 1 · 717s/条</b>——人脸/印花/行走位移画质优于 5B 同镜头，12 分钟级；速度档为 5B 20 步的 3.5 倍耗时换更高画质（对照条见上）</td></tr>
    <tr><td class="k">判负 · TI2V-5B 纯文生</td><td class="v">两个 prompt（丝绸飘动）输出森林/花园男子——<b>与文本完全无关</b>，复现两次坐实，失败样本随包归档</td></tr>
  </table>

  <div style="height:2.5mm"></div>
  <div class="sub"><b>选型结论</b>　①电商 SKU 批产视频用 5B I2V 20 步（约 3.4 分钟/条，单卡日产能百条级）；②换装转场等叙事镜头用 FLF2V 14B；③Lightning 4 步适合快速预览档与抽卡提速；④纯文生需求不在端侧 5B 能力内。<b>评测边界</b>　审片为人工五维评分（见 04D），尚未引入 VBench 等自动指标；14B 单条耗时受权重加载方式影响大，数字为单次实测。</div>
  <div class="pagefoot"><span>04B 视频技术选型与评测</span><span>11</span></div>
</div>

<!-- P12 04D 视频工程链路与交付 -->
<div class="page">
  <div class="head"><div class="no">04C</div><div class="t">视频工程链路与交付</div>
    <div class="en">PIPELINE & QA · IV</div></div>
  <div class="sub">从生成到交付的完整工程链：<b>首帧裁片（人脸偏移对齐）→ 参数化工作流 → 看门狗调度 → 五维审片（多 seed 重掷）→ 剪辑打包（reel/胶片条/GIF）</b>，与图片管线共用 comfy_api 调度层。</div>

  <div style="display:flex; gap:6mm;">
    <div style="flex:1.2;">
      <table class="kv">
        <tr><td class="k">五维审片（0-2 分×5）</td><td class="v">时序稳定性 / 身份一致 / 服装一致 / 动作自然 / 画质与文本符合——<b>总分 ≥8 且无 0 分</b>入册；同镜头重掷上限 4 seed，超限降级并如实记录</td></tr>
        <tr><td class="k">实测通过率</td><td class="v">首轮 11 条 6 过 4 重掷 1 判负；二轮重掷 4/4 通过——<b>幻觉手势为主要淘汰原因</b>（掏纸巾/凭空皮包/抬手鬼影/摆臂糊块各 1 例）</td></tr>
        <tr><td class="k">防幻觉对策</td><td class="v">静止镜头 prompt 显式写死"双臂下垂/无手势/无物件" + 首帧裁片避开手部 + 逐帧放大目检手部区域</td></tr>
        <tr><td class="k">良性幻觉个案</td><td class="v">托脸姿势/编织手袋等形态完好的自发道具按个案放行，如实入册</td></tr>
      </table>
    </div>
  </div>

  <div style="height:2.5mm"></div>
  <div style="display:flex; gap:6mm;">
    <div class="card" style="flex:1; padding:8px 10px;">
      <div style="font-size:9.5px; font-weight:700; margin-bottom:1.5mm;">显存模式实测（判负记录）</div>
      <div style="font-size:8.5px; color:var(--muted); line-height:1.7;">动态显存模式（异步双流 offload）在本机 cu130/pytorch 2.13/ComfyUI 0.34 下对两个 14B fp8 权重<b>采样启动即抛 OSError Errno 22</b>（三次复现）；回退静态显存模式可正常采样但 ≈250s/步。结论：16GB 卡跑 14B <b>可用但慢</b>，模式选型必须实机验证。</div>
    </div>
    <div class="card" style="flex:1; padding:8px 10px;">
      <div style="font-size:9.5px; font-weight:700; margin-bottom:1.5mm;">两个版本坑</div>
      <div style="font-size:8.5px; color:var(--muted); line-height:1.7;">新版 ComfyUI 的 WanFirstLastFrameToVideo 把 clip_vision 拆为 start/end 双输入（旧签名直接 TypeError）；Wan 2.2 必须 48 通道专用 VAE。API 工作流需对安装版本核对节点签名。</div>
    </div>
    <div class="card" style="flex:1; padding:8px 10px;">
      <div style="font-size:9.5px; font-weight:700; margin-bottom:1.5mm;">调度纪律</div>
      <div style="font-size:8.5px; color:var(--muted); line-height:1.7;">沿用图片管线看门狗（单条超时自动重启防 RAM 页交换）；14B 路线改直连队列避免重启丢失动态显存配置；剪辑链 conform 强制 24fps 防混帧率。</div>
    </div>
  </div>

  <div style="height:2.5mm"></div>
  <table class="kv">
    <tr><td class="k" style="width:26mm;">视频交付清单</td><td class="v">10 条终选 mp4（走秀/姿态/回眸×2/风吹裙摆/奶油室内/街拍/面料微距/首尾帧换装转场/14B Lightning）+ <b>30 秒 reel 混剪</b>（字幕卡+淡入淡出，24fps 归一）+ 全部胶片条与首帧静图 —— 规范命名随精选包交付，可直接进详情页/种草/直播轮播位。</td></tr>
    <tr><td class="k">已知限制（如实）</td><td class="v">①5B 动作幅度保守，成片级走秀需 14B 原生或云端；②静止镜头偶发自发手势幻觉，靠 prompt 约束+审片拦截；③14B 端侧单条耗时仍在 10 分钟级，批产需云端/多卡；④视频尚无全自动质检（人工五维审片兜底）。</td></tr>
    <tr><td class="k">下一迭代</td><td class="v">全 SKU 视频批产调度 · 14B 原生 20 步对照（权重已就位）· 云端 API 路线对比（接入位已预留）· VBench 自动评测。</td></tr>
  </table>
  <div class="pagefoot"><span>04C 视频工程链路与交付</span><span>12</span></div>
</div>

<!-- P13 落地与合规 -->'''

OLD_START = '<!-- P8 模特视频化 -->'
OLD_END = '<!-- P9 落地与合规 -->'

with open(HTML, encoding="utf-8") as f:
    s = f.read()

i0 = s.find(OLD_START)
i1 = s.find(OLD_END)
assert i0 != -1 and i1 != -1 and i0 < i1, (i0, i1)
s = s[:i0] + NEW.lstrip("\n") + s[i1 + len(OLD_END):]

# 落地与合规页码 10 -> 13
s = s.replace('<div class="pagefoot"><span>05 落地与合规</span><span>10</span></div>',
              '<div class="pagefoot"><span>05 落地与合规</span><span>13</span></div>')
# 封面副标题加 AI 视频生成
s = s.replace('服装智能换装 / 动作裂变 / 图像净化 · [电话已隐去]',
              '服装智能换装 / 动作裂变 / 图像净化 / AI 视频生成 · [电话已隐去]')
# 封底技术栈更新
s = s.replace('技术栈 — Qwen-Image-Edit-2511 指令编辑 / Wan 2.2 图生视频 / ComfyUI API 工作流（含冻结看门狗）/ SDXL 对照基线 / InsightFace + CLIP + DWPose 量化评测',
              '技术栈 — Qwen-Image-Edit-2511 指令编辑 / Wan 2.2 图生视频 / 首尾帧转场 FLF2V-14B 与 Lightning 加速端侧实测 / ComfyUI API 工作流（冻结看门狗 + 动态显存调优）/ SDXL 对照基线 / InsightFace + CLIP + DWPose 量化评测')
# 封底大标题保持; 页脚计数由渲染脚本核对

with open(HTML, "w", encoding="utf-8") as f:
    f.write(s)
n = s.count('class="page"')
print("HTML rewritten, pages:", n)
