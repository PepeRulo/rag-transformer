# Author: Jose
# Python 3.8.1

from typing import Tuple, Dict, List
from collections import defaultdict
import sys
import data.PKDataset


def rag_dataset_pattern_extractor(pattern_length=8) -> Dict[int, List[Tuple[int, str]]]:
    """ Gets the rag dataset onset patterns with their occurrence proportion.

    The patterns returned correspond to every measure of all the songs in
    the rag dataset. They will be of the length specified by `pattern_length`,
    which is 8 by default but may be any multiple of 8, causing them to be
    stretched by padding them with the necessary '0's after each onset.

    Note that:
        - One of the xmk songs ("kleine.xmk") goes into 16th note level detail;
          this is an example of a song that would require a minimum
          `pattern_length` of 16 (based on its shortest note). If 8 is given
          instead, get_onset_pattern() will fail.

    Equivalent in Java code:
        Done by reading a cryptic file in the project called "table.csv".

    :param int pattern_length: must be a multiple of 8.
    :return: a dictionary mapping number of onsets to each pattern's number
             of occurrences in the dataset over the total occurrences of its
             number of onsets.
    """
    if pattern_length % 8 != 0:
        sys.exit("The length of patterns must be a multiple of 8.")

    dataset_patterns = {}
    pkdata = data.PKDataset.PKDataset()
    for title in pkdata.get_all_titles():
        series = pkdata.get_best_version_of_rag(title,
                                                accept_no_silence_at_start=True,  # FIXME modify args?
                                                quant_cutoff=.95)
        if series is not None:
            fileid = series['fileid']
            song_patterns = pkdata.get_melody_bips(fileid)
            if pattern_length > 8:
                stretched_song_patterns = []
                for pattern in song_patterns:
                    stretched_pattern = ''
                    for char in pattern:
                        stretched_pattern += char
                        stretched_pattern += '0' * (int(pattern_length / 8) - 1)
                    stretched_song_patterns.append(stretched_pattern)
                dataset_patterns[fileid] = stretched_song_patterns
            else:
                dataset_patterns[fileid] = song_patterns

    dataset_patterns = format_dataset_patterns(dataset_patterns)

    return dataset_patterns


def format_dataset_patterns(dataset_patterns) -> Dict[int, List[Tuple[int, str]]]:
    """ Extracts useful information from the `dataset_patterns` dictionary.

    Group all patterns by their number of onsets and obtain their occurrence
    proportion. Note that the proportions in each list corresponding to a
    number of onsets add up to 1 (rather than being the true proportions of a
    pattern in the dataset) so that np.random.choice() works in algorithm_1.py.

    FIXME (consider that):
        - As stated above, each pattern's proportion is with respect to its
          onset count total, not the total number of pattern occurrences.
        - Every single pattern's occurrences and onset frequencies are
          counted (even if the pattern repeats in the same song) to calculate
          the proportions.

    Called by (depends on) rag_dataset_pattern_extractor().

    :param Dict dataset_patterns: a mapping of each song ID to its patterns.
    :return: a dictionary mapping number of onsets to each pattern's number
             of occurrences in the dataset over the total occurrences of its
             number of onsets.
    """
    pattern_occurrences = defaultdict(int)
    onset_frequencies = defaultdict(int)
    for patterns in dataset_patterns.values():
        for pattern in patterns:
            pattern_occurrences[pattern] += 1
            onset_frequencies[pattern.count('1')] += 1

    patterns_by_onsets = defaultdict(list)
    for pattern, occurrences in pattern_occurrences.items():
        onset_total = onset_frequencies[pattern.count('1')]
        patterns_by_onsets[pattern.count('1')].append((occurrences / onset_total, pattern))

    return patterns_by_onsets


def song_patterns_extractor(filename, pattern_length=8) -> List[str]:
    """ Gets all the patterns for an xmk song.

    :param str filename: the xmk file.
    :param int pattern_length:
    :return: the list of patterns corresponding to every measure of the song.
    """
    _, _, _, song = read_xmk(filename)
    song_patterns = []
    for measure in song.values():
        # If note is a rest (-1), signal it by making its note value negative.
        note_values = [line[0] if line[1] != -1 else (-line[0][0], -line[0][1]) for line in measure]
        try:
            measure_pattern = get_onset_pattern(note_values, pattern_length)
        except ValueError:
            raise  # relays error message.
        song_patterns.append(measure_pattern)
    return song_patterns


def get_onset_pattern(note_values, pattern_length=8) -> str:
    """ Converts one measure of the song into an onset pattern.

    The binary onset pattern returned contains '1's and '0's. The '1's
    correspond to onsets and the '0's represent either a held note or a period
    of rest.

    Note that:
        - Even though rests (-1s in the xmk file) do not yield an onset, they
          have to be passed to this function because they might occur at the
          beginning of the measure. The rest value (type; "duration) is passed
          as a regular tuple in `note_values` but with negative elements just
          to signal that it corresponds to a rest.
        - This function only ensures that the note durations given
          (corresponding to one measure) do not exceed 1 (a whole note), as
          that would indicate (for our particular purposes) a musical error
          that should be corrected in the xmk file. The check is done by
          ensuring that all the onsets can fit in the pattern according to its
          `pattern_length`. This function does not, however, directly guarantee
          that the time signature of the underlying song is respected!

    Called by (depends on) song_patterns_extractor().

    Equivalent in Java code:
        Optimized version of MeasureAnalyzer.getRhythm() in
        Midireader/midiReader/src/midireader/processingXmk/MeasureAnalyzer.java.
        That code is too cryptic and slower than it should be, but this more
        succinct interpretation is correct as checked by
        song_transformer.compare_with_java_patterns().

    :param List note_values: the type/"duration" of note, not the actual MIDI
                             note.
    :param int pattern_length:
    :return: the onset pattern string corresponding to one measure of the song.
    """
    durations = [abs(note[0]) for note in note_values]
    fractions = [abs(note[1]) for note in note_values]
    rests = [False if note[0] >= 0 else True for note in note_values]

    # Safety checks.
    for fraction in fractions:
        if pattern_length % fraction != 0:
            raise ValueError("Onsets cannot be evenly divided.")
    fraction_sum = 0
    for i in range(len(durations)):
        fraction_sum += (pattern_length / fractions[i]) * durations[i]
    if fraction_sum > pattern_length:
        raise ValueError(f"Onset pattern does not fit in {pattern_length} characters.")

    pattern = ''
    for i in range(len(durations)):
        if not rests[i]:
            pattern += '1'
        else:
            pattern += '0'
        amount_held = int((pattern_length / fractions[i]) * durations[i])
        pattern += '0' * (amount_held - 1)

    # Safety check: in case xmk file did not account for all the beats in a
    # measure (to add to a whole measure).
    if len(pattern) < pattern_length:
        pattern += '0' * (pattern_length - len(pattern))

    return pattern


def get_song_notes(filename) -> Dict[int, List[int]]:
    """ Gets the MIDI notes for each measure of the song.

    :param str filename: the xmk file.
    :return: a dictionary mapping the measure number to its list of notes.
    """
    _, _, _, song = read_xmk(filename)
    notes = defaultdict(list)
    for measure_number, measure in song.items():
        for onset in measure:
            note = onset[1]
            notes[measure_number].append(note)
    return notes


def get_song_chords(filename) -> Dict[int, List[List[int]]]:
    """ Gets the MIDI notes for each chord in every measure of the song.

    :param str filename: the xmk file.
    :return: a dictionary mapping the measure number to its list of chords.
    """
    _, _, _, song = read_xmk(filename)
    chords = defaultdict(list)
    for measure_number, measure in song.items():
        for onset in measure:
            chord = onset[2]
            if not chords[measure_number]:
                chords[measure_number].append(chord)
            else:
                if chord != chords[measure_number][-1]:
                    chords[measure_number].append(chord)
    return chords


def read_xmk(filename) -> Tuple[int, int, int, Dict[int, List]]:
    """ Returns the information contained in an xmk file.

    Note that:
        - each onset (or rest) in a measure contains three elements (the note
          value, the MIDI note (or -1 for a rest), and the chord currently
          playing at that onset). This is what each line within a measure in
          the xmk file represents.
        - there are not necessarily `beats_per_measure` instances of `onset`
          for the measures, so the time signature is not enforced.
        - the numbers in the xmk file are not separated by spaces but tabs
          (doesn't cause a problem).
        -

    Equivalent in Java code:
        Optimized version of xmReader.xmRead() (xmReader.xmTakeIn()), found
        in Midireader/midiReader/src/midireader/inputXmk/xmReader.java.

    :param str filename: the xmk song.
    :return: a tuple containing
             - the top number (beats per measure) of the song's time signature.
             - the bottom number (beat unit) of the song's time signature.
             - the song's beats per minute.
             - the song — stored as a dictionary mapping the measure number to
               its corresponding MIDI notes with their note values as well as
               its chords' MIDI notes.
    """
    with open(filename) as file:
        header = get_time_signature(file.readline())
        beats_per_measure = header[0]
        beat_unit = header[1]
        beats_per_minute = header[2]

        song = {}
        measure = None
        for line in file:
            if line.startswith("=end"):  # not all files have this.
                continue
            elif line.startswith('='):
                measure = int(line[1:])
                song[measure] = []
            else:
                line = line.split()
                note_duration = tuple(map(int, line[0].split('/')))
                note = int(line[1])
                chord = []

                if line[2] == "-1":
                    chord = -1
                elif '[' not in line[2]:
                    chord_root = int(line[2])
                    chord.append(chord_root)
                    chord.append(chord_root + 4)
                    chord.append(chord_root + 7)
                else:
                    modifier_index = line[2].index("[")
                    chord_root = int(line[2][:modifier_index])
                    chord.append(chord_root)
                    chord.append(chord_root + 4)
                    chord.append(chord_root + 7)

                    modifiers = line[2][modifier_index+1:]
                    if 'm' in modifiers:    # minor
                        chord[1] = chord_root + 3
                    elif '2' in modifiers:  # sus2
                        chord[1] = chord_root + 2
                    elif '4' in modifiers:  # sus4
                        chord[1] = chord_root + 5
                    elif 'd' in modifiers:    # diminished
                        chord[1] = chord_root + 3
                        chord[2] = chord_root + 6
                    elif 'a' in modifiers:  # augmented
                        chord[2] = chord_root + 8
                    if '6' in modifiers:    # six
                        chord.append(chord_root + 8)
                    if '7' in modifiers:    # seven
                        chord.append(chord_root + 10)

                onset = [note_duration, note, chord]
                song[measure].append(onset)
    return beats_per_measure, beat_unit, beats_per_minute, song


def get_time_signature(line) -> List[int]:
    """ Gets the information at the top of the xmk file.

    Called by (depends on) read_xmk().

    :param str line: the top line of the xmk file.
    :return: a list containing
             - the top number (beats per measure) of the song's time signature.
             - the bottom number (beat unit) of the song's time signature.
             - the song's beats per minute.
    """
    time_signature = []
    for num in line.split('[')[1:]:
        time_signature.append(int(num.replace(']', '')))
    return time_signature


if __name__ == '__main__':
    pass


# Not used #

# def get_song_notes_with_time(filename) -> List[Tuple[int, Tuple[int, int]]]:
#     """ Get every MIDI note in the song with its start and end time.
#
#     Equivalent in Java code:
#         Optimized version of xmPlayer.xmPlay() (xmPlayer.xmkPlayMel()), found
#         in Midireader/midiReader/src/midireader/processingXmk/xmPlayer.java.
#         Note that xmPlayer.java @ line 61 never evaluates to true.
#
#
#     :param str filename: the xmk file.
#     :return: a list containing the song's notes with their start and end time
#              (time at which they are played) measured in milliseconds.
#     """
#     _, _, beats_per_minute, song = read_xmk(filename)
#     # How fast the MIDI file should go. (This formula calculates _, see more in _.com)
#     # Modify PPQ for pattern_length.
#     speed = 60000 / (beats_per_minute * 4)  # (xmkPlayMel @ line 44 is wrong, FunctionCallers.java line 295 is right.)
#     notes = []
#     playing_time = 0
#
#     # Dictionaries maintain insertion order, so the measures are stored in
#     # ascending order.
#     for measure in song.values():
#         for onset in measure:
#             note = onset[1]
#             duration = speed * (onset[0][0]/onset[0][1]) # i.e. speed * type of note
#             if note != -1:
#                 start = playing_time
#                 end = start + duration
#                 notes.append((note, (start, end)))
#             playing_time += duration
#
#     return notes

# def get_song_measures(filename) -> int:
#     """ Gets the number of measures in a song.
#
#     Equivalent in Java code:
#         Optimized version of basicTransformations.measures() in
#         Midireader/midiReader/src/midireader/auxClasses/basicTransformations.java.
#         That Java version gets it wrong for "danceSugarPlum.xmk".
#
#     :param str filename: the xmk file.
#     :return: the number of measures in a song.
#     """
#     _, _, _, song = read_xmk(filename)
#     return len(song)
