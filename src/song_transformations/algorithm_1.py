# Author: Jose
# Python 3.8.1

from typing import Dict, List, Tuple
import numpy as np
import random
import music21
# Convenient music21 commands:
#   Note().nameWithOctave
#   Note().duration.type and Note().dots()
#   Chord().pitchedCommonName
#   .show() for multiple objects


# "Algorithm 1" from 2017 paper.
# @args:
# song_notes: notes of the input song (with __) that will remain the same
# for the new song.
# song_patterns: each binary onset pattern represents one measure of the
# song.
# dataset_patterns: [MUST BE IN THE FORM OF!!!!!!!!!!!!!] a list of lists, each describing the unique
# patterns in the dataset, containing number of onsets, pattern
# frequency in dataset, and the actual pattern, all as strings.
# A while is not necessary (as in the algorithm's description) because
# of the possibility that no rules can be generated (having the while
# would just cause an infinite loop).
#
# Optimized version of RhythmChanger.makeRules() and RhythmChanger2.changeSongSync() in
# Midireader/midiReader/src/midireader/processingXmk/RhythmChanger.java and
# Midireader/midiReader/src/midireader/processingXmk/RhythmChanger2.java
#
# For music21 reference: http://web.mit.edu/music21/doc/usersGuide/usersGuide_03_pitches.html#usersguide-03-pitches
#
# SOLVE:
# - in case the if below y is not satisfied, pick another y,
#   that's what the while loop was for!!!
# - y may not exist (-> only could happens if
#   dataset_patterns[num_onsets] does not exist)
# ✓ the dataset_patterns are not in the format i thought at the start,
#   -> put it in that format (for choice() to work)!
# - once there's a y, break from while
# - MAJOR ISSUE: MAKE SURE WHILE LOOP DOESN'T RUN INFINITELY
#
# Suggestion: there's no value in making a weighted choice vs ordering the
#             pool of potential y's by frequency and pop one by one until
#             obtaining a suitable y.
def algorithm_1(song_notes, song_chords, song_patterns, dataset_patterns, pattern_length):
    unique_song_patterns = []
    for pattern in song_patterns:
        if pattern not in unique_song_patterns:  # could optimize by using a dict instead.
            unique_song_patterns.append(pattern)

    rules = {}
    for x in unique_song_patterns:
        num_onsets = x.count('1')
        freq = [tup[0] for tup in dataset_patterns[num_onsets]]
        patterns = [tup[1] for tup in dataset_patterns[num_onsets]]
        rule_generated = False
        while not rule_generated:  # AND TIME < 2 SECONDS
            y = np.random.choice(patterns, p=freq)
            if x != y and onset_distance(x, y) <= pattern_length / 2:
                rules[x] = y
                print(f"Rule added: {x} -> {y}")  # -> add how popular y and whether rest at the beginning or not (caused by syncopation) <- push for those to happen!
                rule_generated = True

    # Create new song by replacing original song's measures that appear in rules[0]

    output_song_melody_measures = music21.stream.Stream()
    for index, pattern in enumerate(song_patterns):
        measure_number = index + 1
        notes = song_notes[measure_number]
        if pattern in rules:
            # If choose to blend them, randomly_change() would be called here. !!!!!
            # As it stands, we've decided to that for every pattern x for which
            # there's a rule, it'll be replaced by y (not combined, literally
            # changed for y).
            output_song_melody_measures.append(generate_melody_measure(notes, rules[pattern]))
        else:
            output_song_melody_measures.append(generate_melody_measure(notes, pattern))

    output_song_harmony_measures = music21.stream.Stream([music21.clef.BassClef()])
    for note_groups in song_chords.values():
        harmony_measure = music21.stream.Measure()
        for note_group in note_groups:
            if note_group == -1:  # Currently ignoring rests for chords!!!!!!!!
                continue
            chord = music21.chord.Chord(note_group)
            harmony_measure.append(chord)
        output_song_harmony_measures.append(harmony_measure)

    score = music21.stream.Score()
    score.insert(0, output_song_melody_measures)
    score.insert(0, output_song_harmony_measures)
    staff_group = music21.layout.StaffGroup([output_song_melody_measures, output_song_harmony_measures], symbol="brace")
    score.insert(0, staff_group)

    return score


# Helper functions #

def onset_distance(pattern1, pattern2) -> int:
    """ Calculate the distance between onsets between two different patterns.

    Since we know that pattern1 and pattern2 are of the same length and that
    they have the same number of onsets, calculating the distance for each one
    of their onsets is straightforward.

    Called by (depends on) algorithm_1().

    :param str pattern1: an onset pattern.
    :param str pattern2: an onset pattern.
    :return: the total distance between the patterns' onsets.
    """
    dist = 0
    indices_1 = []
    indices_2 = []
    for i in range(len(pattern1)):
        if pattern1[i] == '1':
            indices_1.append(i)
        if pattern2[i] == '1':
            indices_2.append(i)
    for i in range(len(indices_1)):
        dist += abs(indices_1[i] - indices_2[i])
    return dist


def generate_melody_measure(notes, pattern):
    """ Obtain the music21 notes for a given measure.

    Two types of patterns (measures) are passed to this function: patterns from
    the xmk input song or patterns coming from the rag dataset (the selected
    `y`'s in `rules`). Remember that '0's in a pattern represent both notes
    being held after an onset and rests, and that patterns may begin with a
    rest.

    :param List notes: a measure's list of MIDI notes (>=0) and/or rests (-1).
    :param str pattern: the measure's onset pattern.
    :return: a music21 stream containing a measure's notes exactly as they will
             be played.
    """
    note_lengths = []
    amount_held = 1
    for index in range(1, len(pattern)):
        if pattern[index] == '0':
            amount_held += 1
        else:
            note_lengths.append(amount_held)
            amount_held = 1
    note_lengths.append(amount_held)

    # unittest: 1) '0' at start . 2) '1' or '-1' at end. Both work!

    # HOW CAN WE BE SO SURE THAT THE NUMBER OF NOTES MATCHES THE
    # NUMBER OF ONSETS __AND__ RESTS IN THE PATTERN IF THE PATTERN
    # IS A RAG DATASET PATTERN!?
    # -> unless the rag dataset patterns account for rests using an indicator
    # ('-1'), the length of the notes list and the length of the note_lengths
    # list will be different. This is not a problem, as the list of notes includes
    # rests, and given the those notes are correctly ordered we can imply where
    # to insert the rest. The issue here is that if rests are not signaled in
    # either the input song or rag dataset patterns, the matched patterns x, y
    # in alg 1 might not be a truly genuine match. You might be comparing a
    # pattern (understood as rhythm) of 1 half note, 1 quarter note and a
    # quarter note rest to one of 2 half notes, calling them equal and
    # either introducing a rest or omitting it in the newly generated output
    # song (depending on which pattern (input or rag) was x and which was y).
    # It might not be a big deal, but you might be calling certain patterns
    # (rhythms) "rag" when they aren't. Since the newly generated song is
    # composed of both the input song's patterns (rhythm) and rag patterns
    # (rhythm) (as determined by alg 1's "rules") this again might not matter,
    # only in precision: the output song could be a little more accurately
    # ragtime if its ragtime parts (those determined by the y patterns) are
    # more accurately chosen (matched) by the algorithm, and that can happen
    # by representing rests in the patterns (so that more details of the rhythm
    # are conveyed), thus making more accurate matches. NEVERTHELESS, FOR THIS
    # TO HAPPEN, THE ONSET_DISTANCE() FUNCTION IN ALG 1 WOULD HAVE TO BE
    # REDEFINED TO TAKE INTO ACCOUNT RESTS AND KNOW HOW TO COMPARE THEM.
    # __ALSO__, SHOULD ELIGIBLE y PATTERNS STILL BE CONSIDERED THOSE WITH THE
    # SAME NUMBER OF ONSETS OR SHOULD IT BE ONSETS ('1's) PLUS RESTS ('-1's).
    # THIS LATTER OPTION MIGHT NOT BE DESIRABLE IF THE RESTS ARE NOT IN THE
    # SAME POSITION IN RELATION TO THE ONSETS. MAYBE THAT CAN BE THE CONSTRAINT
    # OF ONSET_DISTANCE() WHETHER RESTS ARE COUNTED OR NOT TO SELECT THE
    # CANDIDATE y's.

    # notes and note_lengths will be the same length for measures without
    # rests. If there's a rest in the measure and the pattern comes from the
    # rag dataset (it's a y) instead than from the input song (just a
    # regular measure) then (AT THIS POINT IN TIME WHERE '-1's HAVEN'T BEEN
    # CODED TO APPEAR IN THE RAG DATASET PATTERNS) they will differ in length.
    #
    # If '-1's are coded to appear in patterns from the rag dataset, then
    # assigning note durations will be as easy as calculating the
    # durations from `note_lengths` for every note in `notes` (generating a
    # music21 object for each). Otherwise, the corresponding note length
    # will have to first be found according to the -1s in `notes` AND the
    # note following it made shorter. BUT BY HOW MUCH!?!?!?!!
    # Only happens when there is a rest (-1) in `notes`.
    if len(notes) != len(note_lengths):
        for i in range(1, len(notes)):  # if before the first onset, already accounted for
            if notes[i] == -1 and note_lengths[i-1] > 0:
                note_lengths.insert(i, 1)  # <- Experiment with rest length
                note_lengths[i-1] -= 1
    # Alternative to reducing previous note by 1: if the pattern starts
    # with 0, put it there; else if it's between two notes in `notes`
    # (or is the last note in `notes`), split the duration of the
    # first one and make half of the hold belong to the Rest.

    melody_measure = music21.stream.Measure()
    for i, note_pitch in enumerate(notes):
        if note_pitch != -1:
            note = music21.note.Note()
            note.pitch.midi = note_pitch
        else:
            note = music21.note.Rest()
        # music21 only understands duration in terms of quarter notes.
        note.duration.quarterLength = (note_lengths[i] / len(pattern)) * 4
        melody_measure.append(note)

    return melody_measure


if __name__ == '__main__':
    pass


# Optimized version (completely changed) of Java code.
def modify_song(song_patterns, rules):
    pass


# The rule contains 2 patterns (one from the input song and one from the
# entire rag dataset) who are close enough to be combined into a
# new pattern (measure) that represents them both (the notes of the input song pattern
# and the rag rhythm of the dataset pattern) which will be generated in midi.
# We know that both patterns are the same length and, from alg 1,
# that both patterns have the same # of onsets.
#
# For now, replace every x in the original song
#
# DO WE WANT THIS? `chance` -> not yet, experiment with it later
#
# Optimized version of randomlyChange() in
# Midireader/midiReader/src/midireader/processingXmk/syncopalooza.java
def randomly_change(rule, chance):
    song_pattern = rule[0]
    rag_pattern = rule[1]

    onsets = song_pattern.count("1")

    song_onset_indices = []
    rag_onset_indices = []
    for i in range(len(song_pattern)):
        if song_pattern[i] == "1":
            song_onset_indices.append(i)
        if rag_pattern[i] == "1":
            rag_onset_indices.append(i)

    for i in range(onsets):
        rand = random.random()
        if chance > rand:
            ind = song_onset_indices[i]
        else:
            ind = rag_onset_indices[i]

        pass
