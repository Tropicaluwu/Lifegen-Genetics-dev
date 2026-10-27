# Queen's Activity
!!! danger
      might have to be moved, doesn't necessarily involve code

The Queen's Activity is an exclusive LifeGen feature involving Queen's. You can find the feature on a Queen's profile above their name (toy mouse icon).

Essentially, a Queen can play with a single kitten a moonskip and affect four kitten exclusive values. These values are then calculated to influence their future facets and apprentice role.

## Activity Functions & Effects

The activity involves two things: the "play" feature, and the impact stats the play feature affects. Every kitten has four additional values: "Courage", "Compassion", "Intelligence", and "Empathy".

- The Queen Activity is a 50/50 chance for a negative or positive effect. The Queen or kittens traits, skill, or exp does not affect the success of the activity.

Those four impact stats influence what role and trait the kitten could potentially have as they hit apprentice age, depending on how low or high the stat is.

"Play" features effects:
```json
"Mossball" affects courage, compassion, and empathy.   
"Clean" affects compassion, empathy, and intelligence.  
"Lecture" affects intelligence and compassion.  
"Playfight" affects courage, intelligence, and empathy.  
"Tell Story" affects compassion, courage, and empathy.  
"Scavenger" hunt affects Intelligence and Courage.
```

### Influenced Role
```json
"Empathy" may influence a Kit to go into the Mediator Role.   
"Intelligence" may influence a Kit to go into the Medicine cat Role.  
"Compassion" may influence a Kit to go into the Queen Role.   
"Courage" may influence a Kit to go into the Warrior role. 
```
When a kitten is in the positives in a stat, they're more likely to become an apprentice for the connected role (Ex: Empathy for mediator). If the number is in the negatives, they will likely not go in the connected role.

* Conekit plays mossball and continues to lose compassion. Conekit, at -3 compassion, will probably not become a Queen. Their courage, instead, is 2. The kit is more likely to become a warrior.

*Notice that I added ‘may’ to each section.* The state of your clan, the kit's existing traits/skills, and the available potential mentors, all still have an effect on which apprentice role a Kit may go into. Yes, the Queen Activity influences role/trait, but typical game mechanics still apply! Keep that in mind.

### Influenced Trait

When a value (compassion, intelligence, courage, empathy) is NOT zero, it calculates the change in a kitten's facet range. This influences what their trait will become once they age into adolescence.

```json
"Courage" decreases stability and lawfulness, and increases aggression and sociability  
"Compassion" decreases aggression and sociability, and increases stability and lawfulness  
"Intelligence" decreases sociability and lawfulness, and increases stability and aggression  
"Empathy" decreases aggression and stability, and increases sociability and lawfulness
```

Since each value affects every aspect of facets, it's a little hard to predict what their facets will turn into without actually calculating it.

The calculation puts a base max at 15 for each facet, so make sure the queen activity values are lower than 10 to avoid crashing or bugs.

### Calculations

!!! warning
      Put math equations here.

(Code for calculating is found in scripts > [events.py](https://github.com/sedgestripe/clangen/blob/release_LifeGen_v0.7.6.4/scripts/events.py) - search # change personality facets)