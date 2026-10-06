import React from 'react';
import {AbsoluteFill, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, continueRender, delayRender} from 'remotion';

export type Scene = {kind: 'title' | 'page' | 'bullets' | 'cta'; text: string; bullets: string[]; seconds: number};
export type Props = {
  width: number; height: number; fps: number;
  scenes: Scene[]; pages: string[];                       // page images live in --public-dir
  palette: {paper: string; ink: string; muted: string; line: string; accent: string; accentInk: string; soft: string; accent2: string};
  fonts: {heading: string; body: string; script: string};  // CSS family names
  fontFiles: {family: string; weight: number; file: string}[];
  title: string;
};

export const sampleProps: Props = {
  width: 1000, height: 1500, fps: 24, title: 'Sample', pages: [],
  scenes: [
    {kind: 'title', text: 'Plan the week you actually have', bullets: [], seconds: 2},
    {kind: 'bullets', text: 'What you get', bullets: ['52 undated weeks', 'Monthly views', 'Goal pages'], seconds: 3},
    {kind: 'cta', text: 'Sample Planner', bullets: [], seconds: 2},
  ],
  palette: {paper: '#fff', ink: '#1d2320', muted: '#5d6762', line: '#dfe3df', accent: '#2f6b57', accentInk: '#fff', soft: '#e9f1ed', accent2: '#c58b4e'},
  fonts: {heading: 'serif', body: 'sans-serif', script: 'cursive'}, fontFiles: [],
};

export const totalFrames = (p: Props) => Math.max(1, Math.round(p.scenes.reduce((a, s) => a + s.seconds, 0) * p.fps));

const ease = (t: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, t)), 3);

const FadeUp: React.FC<{start?: number; dur?: number; children: React.ReactNode; style?: React.CSSProperties}> = ({start = 0, dur = 0.5, children, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = ease((frame / fps - start) / dur);
  return <div style={{opacity: p, transform: `translateY(${(1 - p) * 40}px)`, ...style}}>{children}</div>;
};

const SceneView: React.FC<{scene: Scene; index: number; p: Props}> = ({scene, index, p}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const u = Math.min(width, height) / 1000;
  const c = p.palette;
  const dark = scene.kind === 'cta';
  const fadeIn = interpolate(frame, [0, 6], [0, 1], {extrapolateRight: 'clamp'});
  const bg = dark ? c.accent : c.soft;
  const ink = dark ? c.accentInk : c.ink;
  const base: React.CSSProperties = {backgroundColor: bg, opacity: fadeIn, fontFamily: p.fonts.body, color: ink, padding: 70 * u, justifyContent: 'center'};
  const blob = <div style={{position: 'absolute', right: -width * 0.25, bottom: -height * 0.15, width: width * 0.75, height: width * 0.75, borderRadius: '50%', background: dark ? c.accent2 : c.accent, opacity: dark ? 1 : 0.18}} />;

  if (scene.kind === 'title' || scene.kind === 'cta') {
    return (
      <AbsoluteFill style={base}>{blob}
        <FadeUp dur={0.7}><div style={{fontFamily: p.fonts.heading, fontWeight: 700, fontSize: 96 * u, lineHeight: 1.08, textAlign: 'center', position: 'relative'}}>{scene.text}</div></FadeUp>
        <FadeUp start={0.6} style={{display: 'flex', justifyContent: 'center', marginTop: 60 * u, position: 'relative'}}>
          <div style={{background: dark ? c.paper : c.accent, color: dark ? c.accent : c.accentInk, borderRadius: 999, padding: `${18 * u}px ${44 * u}px`, fontWeight: 700, letterSpacing: 2, fontSize: 30 * u}}>INSTANT DOWNLOAD</div>
        </FadeUp>
      </AbsoluteFill>
    );
  }
  if (scene.kind === 'page') {
    const src = p.pages.length ? p.pages[index % p.pages.length] : null;
    const zoom = 1 + 0.07 * (frame / (scene.seconds * fps));
    const slide = (1 - ease(frame / fps / 0.6)) * height * 0.12;
    return (
      <AbsoluteFill style={{...base, alignItems: 'center'}}>{blob}
        {src && <Img src={staticFile(src)} style={{height: height * 0.62, transform: `translateY(${slide}px) scale(${zoom})`, borderRadius: 14, boxShadow: '0 30px 70px rgba(0,0,0,.28)', position: 'relative', marginTop: -80 * u}} />}
        <FadeUp start={0.3} style={{position: 'absolute', bottom: height * 0.1, left: 0, right: 0, textAlign: 'center', fontFamily: p.fonts.script, fontSize: 74 * u, color: c.accent}}>{scene.text}</FadeUp>
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={base}>{blob}
      <FadeUp><div style={{color: c.accent, fontWeight: 700, letterSpacing: 4, fontSize: 40 * u, marginBottom: 50 * u, position: 'relative'}}>{scene.text.toUpperCase()}</div></FadeUp>
      {scene.bullets.map((b, i) => {
        const pop = spring({frame: frame - (0.4 + i * 0.45) * fps, fps, config: {damping: 14}});
        return (
          <div key={i} style={{display: 'flex', alignItems: 'center', marginBottom: 46 * u, opacity: Math.min(1, pop), transform: `translateX(${(1 - Math.min(1, pop)) * 40}px)`, position: 'relative'}}>
            <div style={{width: 60 * u, height: 60 * u, borderRadius: '50%', background: c.accent, color: c.accentInk, textAlign: 'center', lineHeight: `${60 * u}px`, fontWeight: 700, fontSize: 34 * u, marginRight: 30 * u, flex: 'none'}}>✓</div>
            <div style={{fontFamily: p.fonts.heading, fontWeight: 700, fontSize: 56 * u}}>{b}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

export const MoneyVideo: React.FC<Props> = (props) => {
  const [handle] = React.useState(() => delayRender('fonts'));
  React.useEffect(() => {
    const faces = props.fontFiles.map((f) => new FontFace(f.family, `url(${staticFile(f.file)})`, {weight: String(f.weight)}).load());
    Promise.all(faces).then((loaded) => { loaded.forEach((f) => (document as any).fonts.add(f)); continueRender(handle); }).catch(() => continueRender(handle));
  }, []);
  const {fps} = useVideoConfig();
  let from = 0;
  return (
    <AbsoluteFill style={{backgroundColor: props.palette.soft}}>
      {props.scenes.map((s, i) => {
        const dur = Math.round(s.seconds * fps);
        const seq = <Sequence key={i} from={from} durationInFrames={dur}><SceneView scene={s} index={i} p={props} /></Sequence>;
        from += dur;
        return seq;
      })}
    </AbsoluteFill>
  );
};
