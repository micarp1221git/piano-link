#!/bin/zsh
# 歌声専用モデル（SOME）で声だけの音を読む → some.mid（テンポ120で書くので、1拍=0.5秒として秒に戻せる）
# 通信を切った状態で動かす（sandbox-exec で network を全部止める）
B=$HOME/code/some-trial
D=$1
cd $B
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
  ./venv/bin/python infer.py --model ckpt/0119_continuous256_5spk/model_ckpt_steps_100000_simplified.ckpt --wav $D/vocals.wav --midi $D/some.mid --tempo 120 2>&1 | tail -8
