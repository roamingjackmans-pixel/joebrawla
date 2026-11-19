// Joe's animation set (moves keyed to frame data: 's' first active frame, 'a' last active, 'e' end).
export default {
    style: {},
    moves: {
      st_L: { keys: [[0, 'stance'], [2, 'jabWind'], ['s', 'jabOut', 'in'], ['a+1', 'jabOut'], ['e', 'stance', 'out']] },
      st_M: { keys: [[0, 'stance'], [4, 'crossWind'], ['s', 'crossOut', 'in'], ['a+2', 'crossOut'], ['e', 'stance', 'out']] },
      st_H: { keys: [[0, 'stance'], [6, 'hayWind', 'out'], ['s', 'hayOut', 'in'], ['a+4', 'hayOut'], ['e', 'stance', 'io']] },
      cr_L: { keys: [[0, 'crouch'], [2, { extends: 'crouch', fr: [0.4, -0.7, 0, 1] }], ['s', 'kickLowCrouch', 'in'], ['a+1', 'kickLowCrouch'], ['e', 'crouch']] },
      cr_M: { keys: [[0, 'crouch'], [4, { extends: 'crouch', fr: [0.35, -0.6, 0, 1] }], ['s', { extends: 'kickLowCrouch', fr: [0.95, -0.84, 0.02, 1], yaw: 25 }, 'in'], ['a+2', { extends: 'kickLowCrouch', fr: [0.95, -0.84, 0.02, 1], yaw: 25 }], ['e', 'crouch']] },
      cr_H: { keys: [[0, 'crouch'], [5, { extends: 'sweep', yaw: 10, fr: [0.5, -0.8, 0.3, 1] }], ['s', 'sweep', 'in'], ['a+6', { extends: 'sweep', yaw: 110 }], ['e', 'crouch']] },
      j_L: { keys: [[0, 'jumpUp'], ['s', 'airKnee', 'out'], ['a', 'airKnee'], ['e', 'jumpUp']] },
      j_M: { keys: [[0, 'jumpUp'], [4, { extends: 'airChop', hr: [0.1, 0.8, 0.1, 1] }], ['s', 'airChop', 'in'], ['a', 'airChop'], ['e', 'jumpUp']] },
      j_H: { keys: [[0, 'jumpUp'], [5, { extends: 'airKnee', fr: [0.3, 0.1, 0, 1] }], ['s', 'airKick', 'in'], ['a', 'airKick'], ['e', 'jumpUp']] },
      doorknocker: { keys: [[0, 'stance'], [10, 'hammerUp', 'out'], ['s', 'hammerDown', 'in'], ['a+5', 'hammerDown'], ['e', 'stance']] },
      launcher: { keys: [[0, 'stance'], [4, { extends: 'stance', pel: [0, -0.15, 0] }], ['s', 'kneeUp', 'in'], ['a+3', 'kneeUp'], ['e', 'stance']] },
      flare: { keys: [[0, 'stance'], [6, 'castWind', 'out'], ['s', 'castOut', 'in'], ['s+8', 'castOut'], ['e', 'stance']] },
      climber: { keys: [[0, 'stance'], [2, 'uppercutLow', 'out'], ['s', 'uppercutHigh', 'in'], ['a', { extends: 'uppercutHigh', fr: [0.1, -0.7, 0, 1] }], ['e', 'stance']] },
      latefee: { keys: [[0, 'stance'], [6, 'kickChamber'], ['s', { extends: 'kickHigh', spin: 0 }, 'in'], ['a', { extends: 'kickHigh', spin: -360 * 1 }], ['e', 'stance']], spinPerHit: true },
      thermos: { keys: [[0, 'stance'], [8, { clip: 'Consume', cf: 0.15 }], [34, { clip: 'Consume', cf: 0.7 }], ['e', 'stance']] },
      surge: { keys: [[0, 'stance'], [4, 'rushPunch'], ['s', 'crossOut'], ['e', 'stance']] },
      mainbreaker: { keys: [[0, 'stance'], [6, 'grabReach'], ['e', 'stance']] },
      generator: { keys: [[0, 'stance'], [8, 'castWind'], ['e', 'stance']] },
    },
    cine: {
      surge: [[0, 'jabOut'], [4, 'crossOut'], [8, 'jabOut'], [12, 'crossOut'], [16, 'jabOut'], [20, 'crossOut'], [24, 'jabOut'], [28, 'crossOut'], [34, 'hayWind'], [42, 'hayOut'], [52, 'uppercutLow'], [62, 'uppercutHigh'], [78, 'stance']],
      mainbreaker: [[0, 'grabReach'], [20, 'hayWind'], [34, 'hayOut'], [60, 'hammerUp'], [86, 'hammerDown'], [120, 'castWind'], [140, 'castOut'], [170, 'stance']],
      generator: [[0, 'castWind'], [30, 'hammerUp'], [50, 'hammerDown'], [90, 'castWind'], [104, 'castOut'], [150, 'stance']],
    },
  };
