# Pirate Character Pack (Kid-Friendly Puppet Style)

Original pirate portraits designed for kids around 7 years old.

## Visual Direction

- Semi-realistic puppet style with felt/fabric texture overlays.
- Big expressive eyes, warm smiles, and clear silhouette variety.
- Adventure-comedy mood inspired by classic pirate games and puppet films.
- No direct copying of existing franchise characters.

## Files

- `captain-brinebeard.svg`
- `first-mate-laughing-lucy.svg`
- `professor-plankton.svg`
- `pegleg-paco.svg`
- `cooky-morgan.svg`
- `young-deckhand-nina.svg`
- `ghostly-gibbs.svg`
- `characters.json` (metadata manifest)

## Technical Notes

- Canvas size: `1024x1024`
- Vector format: `SVG` (clean for scaling and later animation)
- Most characters include felt-like texture filters and stitch-style accents.
- Circular backdrop included for portrait/UI use.

## Integration Hint (pygame)

`pygame` does not natively render SVG. Convert to PNG first:

```bash
# Example with ImageMagick
magick assets/characters/captain-brinebeard.svg assets/characters/captain-brinebeard.png
```

Then in code:

```python
pirate_img = pygame.image.load("assets/characters/captain-brinebeard.png").convert_alpha()
pirate_img = pygame.transform.smoothscale(pirate_img, (280, 280))
screen.blit(pirate_img, (560, 180))
```
