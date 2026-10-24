"""Moonrise intro animation markup for Cadence."""

from __future__ import annotations
def moonrise_markup() -> str:
    stars = "".join(
        f'<span class="a" style="left:{(i*37)%100}%;top:{(i*53)%70}%;width:{1+(i%3)}px;height:{1+(i%3)}px;animation-delay:{(i%5)*.6}s;"></span>'
        for i in range(24)
    )
    rays = "".join(f'<div class="b" style="transform:rotate({i*45}deg);"></div>' for i in range(8))
    sparkles = "".join(
        f'<div class="c" style="transform:translate(-50%,-50%) rotate({i*30}deg) translateX({60+(i%3)*18}px);"><svg viewBox="0 0 14 14"><path d="M0-7L1.8-1.8 7 0 1.8 1.8 0 7-1.8 1.8-7 0-1.8-1.8Z"/></svg></div>'
        for i in range(8)
    )
    return (
        '<style>'
        '.s{position:fixed;inset:0;z-index:9999;overflow:hidden;background:linear-gradient(180deg,#3B0A14 0%,#5A0F1C 22%,#7C1730 48%,#9B2A40 70%,#8E2B45 100%);animation:k0 .4s ease-out both;}'
        '@keyframes k0{from{opacity:0}to{opacity:1}}'
        '.a{position:absolute;border-radius:999px;background:#F3E9D2;opacity:.6;animation:k1 3s ease-in-out infinite;}'
        '@keyframes k1{0%,100%{opacity:.2}50%{opacity:.8}}'
        '.d{position:absolute;left:50%;top:30%;width:160px;height:160px;margin:-80px 0 0 -80px;border-radius:50%;background:radial-gradient(circle,rgba(243,220,154,.6) 0%,rgba(243,220,154,0) 70%);opacity:calc(var(--shine,0)*.6);transform:scale(calc(1+var(--shine,0)*1.4));transition:opacity .5s ease,transform .8s ease;pointer-events:none;}'
        '.e{position:absolute;left:50%;top:30%;width:220px;height:220px;margin:-110px 0 0 -110px;opacity:var(--shine,0);transition:opacity .5s ease;animation:k2 12s linear infinite;pointer-events:none;}'
        '@keyframes k2{from{transform:rotate(0)}to{transform:rotate(360deg)}}'
        '.b{position:absolute;left:50%;top:0;width:1px;height:100%;background:linear-gradient(180deg,rgba(243,220,154,.55),transparent);transform-origin:center;}'
        '.f{position:absolute;inset:0;pointer-events:none;}'
        '.z{position:absolute;inset:0;pointer-events:none;}'
        '.c{position:absolute;left:50%;top:30%;width:14px;height:14px;opacity:calc(var(--shine,0)*.8);transition:opacity .4s ease,transform .8s ease;}'
        '.c svg{width:100%;height:100%;fill:#F3DC9A;}'
        '.s[data-shine="1"] .c{opacity:.8;}'
        '.g{position:absolute;left:50%;top:72%;transform:translate(-50%,0);animation:k3 3.2s cubic-bezier(.2,.7,.2,1) forwards;}'
        '@keyframes k3{0%{top:78%}100%{top:30%}}'
        '.h{position:absolute;inset:-36px;border-radius:50%;background:radial-gradient(circle,rgba(243,220,154,.45) 0%,rgba(243,220,154,0) 70%);opacity:calc(.5+var(--shine,0)*.4);transition:opacity .6s ease;}'
        '.i{position:relative;width:118px;height:118px;border-radius:50%;background:#F3DC9A;overflow:hidden;box-shadow:0 0 40px rgba(243,220,154,.35);}'
        '.j{position:absolute;inset:0;border-radius:50%;background:#3B0A14;transform:translateX(calc(var(--lit,0)*118px));transition:transform .45s ease;}'
        '.k{position:absolute;inset:0;opacity:var(--shine,0);transition:opacity .6s ease;}'
        '.k .l{position:absolute;top:46px;width:6px;height:3px;border-radius:3px;background:rgba(90,15,28,.7);}'
        '.k .l.x{left:34px;}.k .l.y{right:34px;}'
        '.k .m{position:absolute;left:50%;top:62px;width:26px;height:12px;margin-left:-13px;border-bottom:2px solid rgba(90,15,28,.7);border-radius:0 0 16px 16px;}'
        '.k .n{position:absolute;top:58px;width:14px;height:8px;border-radius:50%;background:rgba(231,135,154,.45);}'
        '.k .n.x{left:20px;}.k .n.y{right:20px;}'
    +

        '.o{position:absolute;left:0;right:0;bottom:0;height:34%;pointer-events:none;}'
        '.p{position:absolute;left:0;width:200%;bottom:0;transform-origin:bottom center;}'
        '.p.q{height:100%;background:linear-gradient(180deg,#7C1730,#5A0F1C);animation:k4 9s linear infinite;transform:scaleY(calc(1-var(--shine,0)*.82));}'
        '.p.r{height:86%;background:rgba(155,42,64,.85);animation:k5 6.5s linear infinite;transform:scaleY(calc(1-var(--shine,0)*.82));}'
        '.p.t{height:72%;background:rgba(196,43,72,.55);animation:k6 4.5s linear infinite;transform:scaleY(calc(1-var(--shine,0)*.82));}'
        '@keyframes k4{0%{transform:translateX(0) scaleY(calc(1-var(--shine,0)*.82))}100%{transform:translateX(-50%) scaleY(calc(1-var(--shine,0)*.82))}}'
        '@keyframes k5{0%{transform:translateX(0) scaleY(calc(1-var(--shine,0)*.82))}100%{transform:translateX(-50%) scaleY(calc(1-var(--shine,0)*.82))}}'
        '@keyframes k6{0%{transform:translateX(0) scaleY(calc(1-var(--shine,0)*.82))}100%{transform:translateX(-50%) scaleY(calc(1-var(--shine,0)*.82))}}'
        '.u{position:absolute;top:0;left:0;width:200%;height:6px;background:linear-gradient(90deg,transparent 0%,rgba(233,212,154,.8) 50%,transparent 100%);animation:k6 4.5s linear infinite;}'
        '.v{position:absolute;left:50%;bottom:4%;width:2px;height:26%;transform:translateX(-50%);background:linear-gradient(180deg,rgba(233,212,154,0),rgba(233,212,154,.55),rgba(233,212,154,0));opacity:calc(.35+var(--shine,0)*.5);transition:opacity .6s ease;}'
        '.w{position:absolute;left:50%;bottom:12%;transform:translateX(-50%);font-family:"Cormorant Garamond",Georgia,serif;font-style:italic;font-size:1.35rem;color:#F3E9D2;text-align:center;}'
        '.x{position:absolute;left:0;right:0;text-align:center;opacity:0;animation:k7 4.5s ease-in-out infinite;}'
        '.x:nth-child(1){animation-delay:0s;}.x:nth-child(2){animation-delay:1.5s;}.x:nth-child(3){animation-delay:3s;}'
        '@keyframes k7{0%{opacity:0;transform:translateY(8px)}15%{opacity:1;transform:translateY(0)}35%{opacity:1;transform:translateY(0)}50%{opacity:0;transform:translateY(-8px)}100%{opacity:0}}'
        '.y{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);}'
        '@media (prefers-reduced-motion:reduce){.s *{animation:none !important;transition:none !important;}.g{top:30% !important;}.j{transform:translateX(118px);}}'
        '</style>'
        '<div class="s" data-shine="0">'
        f'<div class="z">{stars}</div>'
        '<div class="d"></div>'
        f'<div class="e">{rays}</div>'
        f'<div class="f">{sparkles}</div>'
        '<div class="g"><div class="h"></div><div class="i"><div class="j"></div><div class="k"><div class="l x"></div><div class="l y"></div><div class="m"></div><div class="n x"></div><div class="n y"></div></div></div></div>'
        '<div class="o"><div class="p q"></div><div class="p r"></div><div class="p t"></div><div class="u"></div></div>'
        '<div class="v"></div>'
        '<div class="w"><div class="x">Preparing your dashboard</div></div>'
        '<div class="y" aria-live="polite">Preparing your dashboard</div>'
        '</div>'
    )


def moonrise_min_seconds(variant: str) -> float:
    return 5.0 if variant == "login" else 3.0

