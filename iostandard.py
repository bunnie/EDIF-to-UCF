''' iostandardMaps is a list of tuples
    the first item in the tuple is a regex that is applied to the net name
    the second item in the tuple is the corresponding I/O standard

    Note that the programming aborts searching once the first match is found.
    Therefore, the last item should always be ".*" as the default match.
'''

iostandardMaps = [ ("^F_.*DQS_[NP]$", 'DIFF_SSTL18_II'),     # matches nets starting with F_ and ending with DQS_N or DQS_P
                   ("F_.*CLK_[NP]$", 'DIFF_SSTL18_II'),      # matches nets starting with F_ and ending with CLK_N or CLK_P
                   ("^F_", 'SSTL18_II'),                     # matches all nets starting with F_
                   ("_[NP]$", 'TMDS_33'),                    # matches all remaining nets with _N or _P at the end. See below.
                   (".*", 'LVCMOS33') ]                      # this is a "default" mapping, everything else gets this

# Note that the mappings are processed in order of specification. So the upper rules has precedence over the lower 
# rules. This means that the "_[NP] mapping at the bottom is overriden by the "F_ ... CLK_[NP]" mapping at the top.
# If your schematic assigns net names with prefixes unique to each subsystem, you can use this feature to split
# out the IO standard for each subsystem while having a default mapping to catch-all others
#
# If you do not want to use any IO standard remappings, just specify an empty list, i.e. comment out the above, and
# uncomment this one line:
#
# iostandardMaps = []


# don't delete the code below, it's needed to make this file work.
def getMapping():
    if( len(iostandardMaps) > 0 ):
        return iostandardMaps
    else:
        return []

