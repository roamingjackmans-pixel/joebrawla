// Per-fighter render settings: which model file, fallbacks while a model is being made, which materials take
// the alternate colours, scale, trail bones and hit-spray style.
export const RENDER = {
  joe: { model: 'joe', fallback: 'mannequin', trail: { L: 'hand_l', M: 'hand_r', H: 'hand_r', kick: 'foot_r' }, spray: 'light' },
  gary: { model: 'gary', tint1: ['gary_top'], tint2: ['gary_bottom'], spray: 'coins' },
  instructor: { model: 'instructor', fallback: 'gary' },
  hollow_knight: { model: 'hollow_knight', spray: 'sparks' },
  brannigan: { model: 'brannigan', fallback: 'gary', spray: 'steam' },
  caretaker: { model: 'caretaker', spray: 'dirt' },
  mother_spore: { model: 'mother_spore', fallback: 'gary', spray: 'spores' },
  bloatking: { model: 'bloatking', fallback: 'caretaker', spray: 'water' },
  vexthorn: { model: 'vexthorn', fallback: 'gary', spray: 'leaves' },
  ignatius: { model: 'ignatius', fallback: 'caretaker', spray: 'embers' },
  aurelia: { model: 'aurelia', fallback: 'gary', spray: 'ice' },
  tock: { model: 'tock', fallback: 'gary', spray: 'gears' },
  landlord: { model: 'landlord', fallback: 'gary', spray: 'void' },
};
