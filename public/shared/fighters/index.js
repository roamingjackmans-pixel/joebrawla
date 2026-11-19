// Every fighter, by id. ORDER is the character-select order (docs/ROSTER.md).
import joe from './joe.js';
import gary from './gary.js';
import instructor from './instructor.js';
import hollow_knight from './hollow_knight.js';
import brannigan from './brannigan.js';
import caretaker from './caretaker.js';
import mother_spore from './mother_spore.js';
import bloatking from './bloatking.js';
import vexthorn from './vexthorn.js';
import ignatius from './ignatius.js';
import aurelia from './aurelia.js';
import tock from './tock.js';
import landlord from './landlord.js';

export const FIGHTERS = { joe, gary, instructor, hollow_knight, brannigan, caretaker, mother_spore, bloatking, vexthorn, ignatius, aurelia, tock, landlord };
export const ORDER = ['joe', 'gary', 'instructor', 'hollow_knight', 'brannigan', 'caretaker', 'mother_spore', 'bloatking', 'vexthorn', 'ignatius', 'aurelia', 'tock', 'landlord'];
/** open from the start; the rest unlock in this order (docs/DESIGN.md §6) */
export const STARTERS = ['joe', 'gary', 'instructor', 'hollow_knight', 'brannigan', 'caretaker'];
export const UNLOCK_ORDER = ['mother_spore', 'bloatking', 'vexthorn', 'ignatius', 'aurelia', 'tock'];
