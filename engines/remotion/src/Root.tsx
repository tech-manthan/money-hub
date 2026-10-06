import React from 'react';
import {Composition} from 'remotion';
import {MoneyVideo, Props, totalFrames, sampleProps} from './MoneyVideo';

export const Root: React.FC = () => (
  <Composition
    id="MoneyVideo"
    component={MoneyVideo}
    width={1000}
    height={1500}
    fps={24}
    durationInFrames={240}
    defaultProps={sampleProps}
    calculateMetadata={({props}: {props: Props}) => ({
      width: props.width,
      height: props.height,
      fps: props.fps,
      durationInFrames: totalFrames(props),
    })}
  />
);
