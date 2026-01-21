# Failure Mode Identification Guide

This guide explains how to identify and label different failure modes when reviewing ARC puzzle reasoning. Use this as a reference when labeling puzzles in the reasoning labeler app.

## Overview

Failure modes are categorized into three main categories:
- **Category A**: Accuracy Failures
- **Category B**: Step Count Issues  
- **Category C**: Visual Fidelity Issues

You can select multiple failure modes for a single puzzle if it exhibits multiple issues.

---

## Category A: Accuracy Failures

These indicate that the model's solution doesn't produce correct outputs.

### A1: Complete Failure (0% Test Accuracy)

**What it means**: The model gets **0% test accuracy** - it fails on all test examples.

**How to identify**:
- Check the test accuracy in the puzzle metrics
- If test accuracy is 0.0 (0%) and there are test examples, this is A1
- The model's generated outputs don't match any expected outputs

**Example**:
- Puzzle has 3 test examples
- Model gets 0 out of 3 correct
- Test accuracy: 0.0 → **A1**

**When to use**: Always check test accuracy first. If it's 0%, mark A1.

---

### A2: Partial Failure (0% < Test Accuracy < 100%)

**What it means**: The model gets **some test examples correct but not all** - partial success.

**How to identify**:
- Test accuracy is greater than 0% but less than 100%
- For example: 1 out of 3 correct = 33.3% accuracy → **A2**
- The model works for some cases but not others

**Example**:
- Puzzle has 4 test examples
- Model gets 2 out of 4 correct
- Test accuracy: 0.5 (50%) → **A2**

**When to use**: Use A2 when the model has partial but incomplete test accuracy.

---

### A3: Training Failure (Training Accuracy < 100%)

**What it means**: The model **fails on training examples** - the steps don't even work on the examples used to generate them.

**How to identify**:
- Check training accuracy in puzzle metrics
- If training accuracy is less than 1.0 (100%), this is A3
- This is a serious issue - the model can't even solve the examples it learned from

**Example**:
- Puzzle has 3 training examples
- Model gets 2 out of 3 correct on training
- Training accuracy: 0.67 (67%) → **A3**

**When to use**: Use A3 when training accuracy is below 100%, even if test accuracy is good. This indicates the steps themselves are flawed.

**Note**: A puzzle can have both A2 and A3 if it fails on both training and test examples.

---

## Category B: Step Count Issues

These indicate problems with the number or structure of reasoning steps.

### B1: Too Many Steps (>10 steps)

**What it means**: The model generated **more than 10 general steps**, indicating overly complex or verbose reasoning.

**How to identify**:
- Check the "Steps" metric in the puzzle header
- If number of steps > 10, this is B1
- Look at the steps list - are there many redundant or overly detailed steps?

**Example**:
- Puzzle shows "Steps: 15" in metrics
- The general steps list has 15 steps
- Many steps seem to repeat similar operations → **B1**

**When to use**: Use B1 when the step count is high and the reasoning seems unnecessarily complex or verbose.

**Heuristic**: Generally, if steps > 10, it's worth checking if the reasoning could be simplified.

---

### B2: Too Few Steps (<2 steps)

**What it means**: The model generated **very few steps** (less than 2), indicating missing intermediate reasoning.

**How to identify**:
- Check the "Steps" metric
- If number of steps < 2, this is B2
- The reasoning seems incomplete or oversimplified

**Example**:
- Puzzle shows "Steps: 1" in metrics
- Only one general step like "analyze the puzzle pattern"
- No detailed breakdown of the transformation → **B2**

**When to use**: Use B2 when the step count is very low and the reasoning lacks detail. This often indicates the model didn't break down the problem properly.

**Note**: For puzzles with only 1-2 training examples, fewer steps might be acceptable. Use judgment.

---

## Category C: Visual Fidelity Issues

These indicate that the visual representations (grids, bounding boxes) don't match the textual descriptions.

### C1: Grid Mismatch

**What it means**: The **grid states don't match what the step describes**.

**How to identify**:
- Look at the `grid_before` and `grid_after` in step details
- Compare them to what the step instruction says should happen
- If the grids don't match the described transformation, this is C1

**Example**:
- Step says: "Find the red object in the top-left corner"
- `grid_before` shows: Red object is in the bottom-right corner → **C1**

**Another example**:
- Step says: "The input grid has 3 objects"
- `grid_before` shows: Only 2 objects visible → **C1**

**When to use**: Use C1 when the visual grid state contradicts what the text says the grid should contain or look like.

**Key question**: "Does the grid_before match what the step says it should be looking at?"

---

### C2: Bbox Misalignment

**What it means**: The **bounding box doesn't correctly highlight the objects** mentioned in the step condition.

**How to identify**:
- Look at the step condition (what objects/regions it's looking for)
- Check if the bbox coordinates actually highlight those objects
- If the bbox is in the wrong location or highlights wrong objects, this is C2

**Example**:
- Step condition: "Find object with color 3 in the center"
- Bbox shows: `[x1: 0, y1: 0, x2: 2, y2: 2]` (top-left corner)
- But color 3 object is actually at center `[x1: 4, y1: 4, x2: 6, y2: 6]` → **C2**

**Another example**:
- Step condition: "Select the largest blue object"
- Bbox highlights: A small blue object instead of the largest one → **C2**

**When to use**: Use C2 when bounding boxes are incorrectly positioned or highlight the wrong objects compared to what the step condition specifies.

**Key question**: "Does the bbox correctly highlight what the condition says to look for?"

---

### C3: Description Mismatch

**What it means**: The **visual result doesn't match the textual description** of what should happen.

**How to identify**:
- Read the step instruction carefully
- Look at the `grid_after` (what actually happened)
- Compare: Does the visual transformation match what the text says?

**Example**:
- Step instruction: "Rotate the object 90 degrees clockwise"
- `grid_after` shows: Object rotated 90 degrees **counter-clockwise** → **C3**

**Another example**:
- Step instruction: "Fill the region with color 3 (green)"
- `grid_after` shows: Region filled with color 5 (orange) instead → **C3**

**Another example**:
- Step instruction: "Move object A to be adjacent to object B"
- `grid_after` shows: Object A moved **away** from object B → **C3**

**When to use**: Use C3 when there's a clear contradiction between what the text says should happen and what the visual shows actually happened.

**Key question**: "If I read the instruction and look at the grid transformation, do they match?"

**This is the most common Category C issue** - models often describe one transformation but execute a different one.

---

## Multiple Failure Modes

A single puzzle can have multiple failure modes. For example:

- **A2 + C3**: Model has partial test accuracy (A2) AND the visual results don't match descriptions (C3)
- **B1 + C2**: Model has too many steps (B1) AND bounding boxes are misaligned (C2)
- **A3 + B2 + C3**: Model fails on training (A3), has too few steps (B2), AND descriptions don't match visuals (C3)

**Select all that apply** when labeling a puzzle.

---

## Quick Reference Checklist

When reviewing a puzzle, check:

1. **Accuracy**:
   - [ ] Test accuracy = 0%? → **A1**
   - [ ] 0% < Test accuracy < 100%? → **A2**
   - [ ] Training accuracy < 100%? → **A3**

2. **Step Count**:
   - [ ] More than 10 steps? → **B1**
   - [ ] Less than 2 steps? → **B2**

3. **Visual Fidelity**:
   - [ ] Grid states don't match step descriptions? → **C1**
   - [ ] Bounding boxes highlight wrong objects? → **C2**
   - [ ] Visual transformations don't match text? → **C3**

---

## Examples from Your Data

Based on your current metrics:
- **C3 is most common** (8 puzzles, 18.6%) - Description mismatches are frequent
- **C2 is second** (6 puzzles, 14.0%) - Bbox misalignment is also common
- **B1 is common** (8 puzzles, 18.6%) - Models often generate too many steps

This suggests models struggle with:
1. **Visual-text alignment** (C3) - describing what they're doing vs. what they actually do
2. **Object localization** (C2) - correctly identifying and highlighting objects
3. **Reasoning conciseness** (B1) - being too verbose in step generation

---

## Tips for Accurate Labeling

1. **Read carefully**: Don't just skim - read the step instructions and compare to visuals
2. **Check multiple examples**: Look at both training and test examples if available
3. **Be consistent**: Use the same criteria across all puzzles
4. **When in doubt**: If you're unsure, you can mark as "Skip - Not Enough Information"
5. **Multiple modes are OK**: A puzzle can legitimately have multiple failure modes

---

## Need Help?

If you're unsure about a failure mode:
- Review the examples above
- Check if the issue matches the description
- When in doubt, add notes in the reasoning field explaining your uncertainty
- You can always go back and edit labels later

