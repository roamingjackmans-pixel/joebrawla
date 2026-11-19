# JoeBrawla — Roster

Thirteen fighters from Dungeon Joe (story: `C:\dev\AverageJoe\DungeonJoe3D\docs\STORY.md`). Each entry has the
**look** (the art brief), the **play style**, the **moves** and their **lines**. Frame data lives in
`public/shared/fighters/<id>.js`; when this page and the data disagree, the data is the truth and this page
gets fixed.

Notation: 5 = neutral, 2 = down, 6 = toward, 4 = away, 236 = quarter-circle forward, 214 = quarter-circle back,
623 = dragon punch, 41236 = half-circle forward, 22 = down-down, [4]6 = charge. "S:" = the Simple-scheme input.
Every fighter also has: standing L/M/H, crouching L/M/H (2H is a sweep or launcher), jumping L/M/H, a throw and
back throw, Breaker, Super Art (236236 / Super), Final Notice (214214 / 2+Super), Overtime Art (Super+S).

---

## Joe — "Apartment 3C" (shoto all-rounder, HP 1000, starts unlocked)

**Who:** Every tenant is "Joe" on the lease. This one went down to find the breaker box at 11:52 p.m. and came
back up forty flights later knowing how to fight.

**Look (new model, 1.82 m):** athletic everyman. UBC Superhero_Male body. Rolled-sleeve charcoal work shirt open
over a white tank top, a little torn; dark work trousers with knee patches; scuffed tan work boots; a tool belt
with a **flashlight holstered on the right hip** and a brass key on a lanyard; hands wrapped in **grey duct
tape** like boxing wraps; messy brown hair, stubble. Accent: a faded orange "3C" patch on the shoulder.
tint1 = shirt, tint2 = trousers.

**Moves**
- 6M **Doorknocker** — overhead hammer-fist.
- 3H **Stairwell Launcher** — rising knee, launches.
- 236 + atk (S) **Flashlight Flare** — a cone of light thrown as a projectile (L slow, H fast; EX two hits, knockdown).
- 623 + atk (6S) **Stair Climber** — jumping uppercut anti-air; H and EX invulnerable to strikes on startup.
- 214 + atk (4S) **Late Fee** — spinning hook kick that travels (L 1 spin, H 3 spins; EX in the air too, j.214).
- 22 + atk (2S) **Thermos Break** — drinks from the Thermos: restores 3 % red health and a sliver of meter
  (punishable; "Still warm. Nobody knows how.").
- Super Art **Power Surge** — dashing flurry of electrified punches ending in an uppercut.
- Final Notice **MAIN BREAKER** — slams the opponent into a wall-sized breaker panel and throws the switch.
- Overtime Art **Backup Generator** — yanks the cord on a generator; the blast lights the whole stage.

**Lines:** intro "Has anyone seen the breaker box?" · win "Lights are back on. Probably." · "I just live
here." · "Forty flights. Every day."

## Gary — "Everything's for sale. Except Gary." (trickster, HP 950, starts unlocked)

**Who:** The wandering merchant. Meet him once and he moves into your broom closet ("a suite").

**Look (DJ3D `gary`, 1.85 m):** as built: wide brimmed hat, mustard tunic, the enormous wooden-frame backpack
of wares (pots, scrolls, lantern, chain). The backpack is part of his moveset.

**Moves**
- 236 + atk (S) **Merchandise Toss** — throws a random ware: pot (arcing, shatters), scroll (straight, fast),
  chain (slow, 3 hits). The ware rotates in a seeded order shown on his HUD.
- 214 + atk (4S) **Haggle** — counter stance; parries a strike, pockets ½ bar of the opponent's meter, shoves.
- 22 + atk (2S) **Mimic Chest** — sets a chest on the floor; it bites anyone who walks within reach (one at a time).
- 623 + atk (6S) **Backpack Swing** — spins the pack overhead, anti-air.
- j.214 + atk (j.S) **Price Drop** — drops a crate diagonally from the air.
- Super Art **Clearance Sale** — merchandise rains across the screen.
- Final Notice **Everything Must Go** — the giant mimic unfolds from his pack and swallows the opponent.
- Overtime Art **Final Offer** — pulls a golden ledger; every ware on screen explodes into coins.

**Lines:** "Everything's for sale." · win "Except Gary." · "No refunds. No receipts. No Gary."

## The Instructor (counter fighter, HP 1000, starts unlocked)

**Who:** Management's orientation officer. Runs the Training Hall. He has trained every Joe. None has passed.

**Look (new model, 1.95 m):** tall, rigid posture. Slate-grey Management dress uniform: high collar, brass
buttons, a crimson sash, pressed trousers tucked into polished black boots, white gloves. Peaked officer's cap
low over the eyes; a whistle on a cord; a **clipboard on his back** and a **black training baton** in the right
hand. Grey moustache. tint1 = uniform, tint2 = sash.

**Moves**
- 214 + atk (4S) **Demonstration** — counter stance; catches a strike and throws with a textbook takedown.
- 236 + atk (S) **Whistle Blast** — short-range sound wave projectile with big pushback.
- 623 + atk (6S) **Pop Quiz** — rising baton strike, anti-air.
- 22 + atk (2S) **Dummy Drop** — a training dummy drops in front of him and absorbs one hit or projectile.
- 6H **Correction** — step-in baton crack, wall splats.
- Super Art **Orientation** — a blur of baton strikes "for your own good".
- Final Notice **Final Exam** — a cinematic grading; the opponent is stamped **F**.
- Overtime Art **Nobody Passes** — clipboard to the face, then the whistle at full volume.

**Lines:** "Again." · "Elbows in." · win "Nobody passes." · vs Joe "You again."

## The Hollow Knight (sword and shield footsies, HP 1050, starts unlocked)

**Who:** A knight who went down the stairs long before Joe and is still guarding a door nobody uses.

**Look (DJ3D `hollow_knight`):** as built: rusted mossy plate, green tabard, kite shield, longsword, a glow of
teal in the visor slit.

**Moves**
- 236 + atk (S) **Shield Charge** — armoured shield rush (absorbs 1 hit; EX 2).
- 623 + atk (6S) **Rising Oath** — rising slash.
- 214 + atk (4S) **Hollow Lunge** — long thrust, punishes from far.
- 22 + atk (2S) **Bulwark** — shield guard that reflects projectiles.
- Super Art **Oath of the Hollow** — a five-cut sword combo.
- Final Notice **Last Watch** — plants the sword; spectral knights strike from both sides.
- Overtime Art **The Door Nobody Uses** — a giant spectral door slams shut on the opponent.

**Lines:** "…" · win "The door stays shut." · "I was told to wait."

## Brannigan (steam boxer, HP 1050, starts unlocked)

**Who:** The building's old boilerman; followed the pipes down to a forge he liked better. Now the Landing's smith.

**Look (DJ3D resident `brannigan`):** as built, plus (if the model allows) brass knuckle-dusters and a pipe wrench
holstered on the back; soot.

**Moves**
- 236 + atk (S) **Boiler Rush** — dashing straight punch (H crosses half the screen).
- 623 + atk (6S) **Price Hike** — uppercut. "Steel's like rent. It only ever goes up."
- 214 + atk (4S) **Wrench Swing** — overhead wrench, ground bounce.
- 22 + atk (2S) **Pressure Valve** — vents steam: his next special is the EX version for free (stacks once).
- Super Art **Rent Goes Up** — a rising combo of punches ending in a steam blast.
- Final Notice **Full Pressure** — hugs the opponent into an exploding boiler.
- Overtime Art **Red Line** — the gauge on his chest hits red; a point-blank steam explosion.

**Lines:** "Steel's like rent." · win "It only ever goes up." · "Mind the pipes."

## The Caretaker (big body, shovel reach, HP 1150, starts unlocked)

**Who:** Ruler of the Mossy Crypt. Buries tenants who fall behind; has fallen behind on the burying.

**Look (DJ3D boss `caretaker`, 2.19 m):** as built: moss-covered hat with mushrooms, huge white moustache with
roots, green coat, leather apron, giant shovel, glowing lantern.

**Moves**
- 236 + atk (S) **Dirt Sweep** — scoops a low arcing clod of dirt.
- 214 + atk (4S) **Overhead Slam** — shovel slam, ground bounce, overhead.
- 22 + atk (2S) **Grave Call** — hands burst from the ground at near / mid / far distance (L/M/H).
- 41236 + atk (6S) **Another One for the Garden** — command grab: plants the opponent head-first.
- j.236 + atk (j.S) **Lantern Toss** — throws the lantern diagonally down; fire on impact.
- Super Art **Last Rites** — sweeping shovel combo ending in a burial.
- Final Notice **The Garden** — dozens of grave hands drag the opponent under; a headstone drops.
- Overtime Art **Fury** — the moss on his hat catches fire; a burning spin.

**Lines:** intro "Another one for the garden." · win "Plenty of room." · "Wipe your feet."

## Mother Spore (zoner, traps, HP 950, unlock 1)

**Who:** Ruler of the Fungal Hollows. Leased the sky's light so her children would never wilt.

**Look (new humanoid model, 2.0 m incl. cap):** a tall, graceful fungal matriarch. Pale mauve skin with fine
gill-like ridges; a **huge flat mushroom cap worn like a wide hat/hood** (rust-red with cream spots) shading
glowing violet eyes; a long layered dress made of mycelium threads and shelf-fungus frills fading into trailing
root tendrils at the hem; long-fingered hands; bioluminescent teal spots that pulse (emissive). A gnarled
mushroom-stalk staff. tint1 = cap, tint2 = dress.

**Moves**
- 236 + atk (S) **Spore Bloom** — a slow drifting spore cloud that lingers (L close, H far).
- 214 + atk (4S) **Tendril Whip** — long low root lash.
- 22 + atk (2S) **Sporeling** — plants a sporeling that hops toward the opponent after a delay (2 max).
- 623 + atk (6S) **Stalk Slam** — a giant mushroom stalk erupts in front of her (anti-air).
- j.S **Cap Glide** — floats slowly down.
- Super Art **Rain of Caps** — mushroom caps rain over the opponent's half.
- Final Notice **Everything Becomes Soil** — the opponent is wrapped in mycelium and blooms.
- Overtime Art **Overtime Bloom** — the whole floor bursts into glowing fungus.

**Lines:** "Hush now." · win "Everything becomes soil in the end." · "Wipe that look off. It grows back."

## The Bloatking (grappler, HP 1250, unlock 2)

**Who:** Ruler of the Drowned Quarter, who traded all the dry land for a crown.

**Look (DJ3D boss `bloatking`, throne removed, 2.2 m):** as built: swollen drowned monarch, barnacled crown,
sceptre, waterlogged regalia, weeds.

**Moves**
- 41236 + atk (6S) **Royal Decree** — command grab; the sceptre seals the verdict (L far reach, H damage).
- 236 + atk (S) **Belch** — short-range wave of bilge, pushes and knocks down.
- 214 + atk (4S) **Crosswave** — sceptre sweep along the floor (low).
- 22 + atk (2S) **Drowning Grasp** — a water tendril grabs at mid range (slow, unblockable, jumpable).
- j.2H **Belly Flop**.
- Super Art **The Court Is in Session** — command-grab super with a rain of gavels.
- Final Notice **The Court Is Underwater** — the stage floods; the opponent is dragged under the waves.
- Overtime Art **Royal Belch** — a full-screen belch.

**Lines:** intro "The court is in session." · win "The court is underwater." · "Bow. Lower. Lower."

## Vexthorn, the Hollow Stag (rushdown, teleport, HP 950, unlock 3)

**Who:** Ruler of the Hollow Forest; his lantern-heart lights the forest's breaker room.

**Look (new model, 2.05 m to antler tips):** a lean, tall stag-headed humanoid. Deer skull-like head with
**enormous branching antlers** strung with autumn leaves and tiny hanging lanterns; a hollow ribcage of bark with
a **glowing amber lantern-heart** inside (emissive); bark-plated shoulders, moss and orange-red leaves on the
shoulders; digitigrade legs ending in hooves; long clawed hands. Colours: dark bark, burnt orange leaves, amber
glow. tint1 = leaves, tint2 = bark.

**Moves**
- 236 + atk (S) **Antler Rush** — lowered-antler charge (H passes through projectiles).
- 214 + atk (4S) **Leaf Step** — vanishes in a swirl of leaves and reappears behind or in front (L/H).
- 623 + atk (6S) **Rising Antler** — antler toss, launches.
- j.2 + atk (j.S) **Hoof Drop** — steep dive kick.
- Super Art **The Hunt** — chases across the screen in five strikes.
- Final Notice **Hollow Heart** — opens his chest; the lantern-heart's light burns the opponent.
- Overtime Art **Last Leaf** — every leaf in the stage becomes a blade.

**Lines:** (he does not speak; a deep bellow) · win card "The forest keeps its own." 

## Foreman Ignatius (armoured heavy, fire, HP 1150, unlock 4)

**Who:** Ruler of the Ashen Forge, which makes the Landlord's locks, keys and chains.

**Look (new model, 2.15 m):** a massive foundry boss. Barrel chest, thick arms; a scorched **leather apron**
over chainmail; one arm in a riveted **iron gauntlet**; a welding-mask helmet with glowing orange eye slits and
a hardhat brim; soot-black skin and a braided beard with ember-lit tips; chains wrapped round one shoulder; a
**huge forge hammer** with a glowing hot head (emissive). tint1 = apron, tint2 = hardhat/trim.

**Moves**
- 236 + atk (S) **Molten Pour** — a wave of molten metal along the floor.
- 623 + atk (6S) **Overtime Swing** — armoured rising hammer, launches.
- 214 + atk (4S) **Anvil Drop** — leaps and slams (overhead, armoured on landing).
- 22 + atk (2S) **Chain Pull** — hooks the opponent and drags them in (mid range).
- Many heavy normals have 1-hit armour.
- Super Art **Clock In** — a three-swing hammer combo with fire.
- Final Notice **Shift's Not Over** — smashes the opponent on an anvil, forges them into a key.
- Overtime Art **Furnace Heart** — the forge erupts.

**Lines:** "Shift's not over till I say it's over." · win "Back to work." · "You're on the clock."

## Saint Aurelia the Unthawed (ice keep-away, hover, HP 900, unlock 5)

**Who:** Ruler of the Frozen Reliquary, still waiting for the heating repairman.

**Look (new model, 1.85 m + halo):** a serene frozen saint. Pale blue-white skin dusted with frost; long white
hair frozen into icicle strands; a **halo of icicles** floating behind the head (emissive pale blue); layered
white-and-gold liturgical robes with a frost-crusted hem and a hanging stole; a tall **crozier staff** topped
with a frozen sunburst; bare feet just off the ground. Eyes closed, glowing faintly. tint1 = robes,
tint2 = stole/gold trim.

**Moves**
- 236 + atk (S) **Frost Lance** — fast ice spear.
- 214 + atk (4S) **Hailstorm** — hail falls at near / mid / far.
- 22 + atk (2S) **Ice Mirror** — a mirror that reflects projectiles and blocks once.
- 623 + atk (6S) **Ascension** — an ice pillar under her (anti-air).
- j.S **Hover** — floats in place for a moment and can cancel into attacks.
- Super Art **Cold Snap** — a blizzard beam.
- Final Notice **Have You Come About the Heating?** — freezes the opponent solid, then shatters the ice.
- Overtime Art **Unthaw** — a holy sun breaks through the ice.

**Lines:** intro "Have you come about the heating?" · win "Someone will be along." · "Mind the draught."

## Archmagister Tock (time tricks, setups, HP 900, unlock 6)

**Who:** Ruler of the Clockwork Citadel, keeper of every lease and late fee.

**Look (new model, 1.80 m):** a gaunt clockwork wizard. Brass-and-walnut automaton body under a deep blue
academic robe with brass trim; a **clock face set into the chest** with moving hands (emissive numerals); a
mortarboard-like hat with a rotating gear crown; a long white beard of brass wire; one monocle glowing;
gear-jointed hands; a staff with a swinging **pendulum**. tint1 = robe, tint2 = trim.

**Moves**
- 236 + atk (S) **Tick Bolt** — a clock hand thrown like a dart (L slow, H fast).
- 214 + atk (4S) **Rewind** — teleports to where he stood one second ago.
- 22 + atk (2S) **Gear Trap** — sets a spinning gear on the floor.
- 623 + atk (6S) **Pendulum** — the pendulum swings up (anti-air).
- Super Art **Overdue** — stops time for 1.5 s.
- Final Notice **You Are Late** — a giant clock face crushes the opponent between its hands.
- Overtime Art **Midnight** — every clock strikes twelve.

**Lines:** intro "You are late." · win "Everyone is always late." · "Tick."

## The Landlord (final boss / secret, HP 1100, unlock: clear the ladder on The Landlord difficulty)

**Who:** Bought the deed to all eight realms. He doesn't conquer; he leases.

**Look (new model, 2.0 m):** a tall, impossibly neat man in a **very good three-piece suit**: deep charcoal
pinstripe, violet silk tie and pocket square, gold watch chain, polished shoes; slicked black hair; a calm,
handsome face with **eyes that are pure black with violet static** (emissive); long fingers; he carries a
**black leather briefcase** and a **gold fountain pen**. Faint violet static flickers at the edges of his
silhouette (VFX in game). tint1 = suit, tint2 = tie/pocket square.

**Moves**
- 236 + atk (S) **Eviction Notice** — a paper notice flies out and curves toward the opponent.
- 41236 + atk (6S) **Sign Here** — command grab; the contract binds and burns.
- 214 + atk (4S) **Void Step** — steps into violet static and out behind.
- 623 + atk (2S) **Briefcase Uppercut** — rising briefcase swing (anti-air).
- Super Art **Late Fees** — compounding hits: each hit stronger than the last.
- Final Notice **The Deep Lease** — drags the opponent into the void beneath the desk.
- Overtime Art **Eviction** — the stage itself is repossessed.
- Boss version (arcade fight 8): three phases — **The Interview** (normal), **The Eviction** (faster, armour on
  specials, notices rain), **The Deep Lease** (the stage turns to void; he grows and hits through block).

**Lines:** intro "Joe. Apartment 3C. You're late with the rent." · win "Your deposit will not be returned." ·
"Sign here. And here."
