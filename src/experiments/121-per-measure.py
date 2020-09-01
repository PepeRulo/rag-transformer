#%%
# experiment - replicate from 2013 paper
# count 121 pattern occurences, tied and untied, grouped by era

# strategy:
# for each piece:
#   - count total bars
#   - count bars that match 121 untied (2 instances)
#   - count bars that match 121 tied (2 instances)

import data.PKDataset
import data.RagDataset
import scipy.stats
import pandas as pd
from collections import Counter
import functions

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

pkdata = data.PKDataset.PKDataset()
rags = data.RagDataset.RagDataset()

rowslist = []

for title in pkdata.get_all_titles():
    series = pkdata.get_best_version_of_rag(title,
                                            accept_no_silence_at_start=True,  # modify this #####
                                            quant_cutoff=.95)
    if series is not None:
        fileid = series['fileid']
        melbips = pkdata.get_melody_bips(fileid) # list of num of measures in the song, each item is 8chars long
        bassbips = pkdata.get_bass_bips(fileid)

        assert len(melbips) == len(bassbips)

        d = {}
        d['fileid'] = fileid

        # initialize vars per song
        barcount = 0
        pattern_count_tied = 0
        pattern_count_tied_aug = 0
        pattern_count_untied = 0
        pattern_count_untied_aug = 0

        for x in range(0, len(melbips)):
            melbip = melbips[x]
            bassbip = bassbips[x]

            # check if we have a next bar, needed for tied 121 pattern across barline
            melbip_nextbar = 'XXXXXXXX'
            if x+1 < len(melbips):
                melbip_nextbar = melbips[x+1]

            # if both mel and bass are silent, don't count either
            if melbip == "00000000" and bassbip == "00000000":
                continue

            if len(melbip) != 8:
                continue

            # we have a good melody bar
            barcount += 1

            # check 121 untied
            if melbip[0:4] == '1101':# or melbip == '10100010':
                pattern_count_untied += 1
                #print('found untied beg', x)
            if melbip[4:8] == '1101':
                pattern_count_untied += 1
                #print('found untied end', x)
            if melbip[2:6] == '1101':
                pattern_count_tied += 1
                #print('found tied middle', x)
            if melbip[6:8] == '11' and melbip_nextbar[0:2] == '01':
                pattern_count_tied += 1
                #print('found tied across bar', x)

            if melbip == '10100010':
                pattern_count_untied_aug += 1
            if melbip[4:8] == '1010' and melbip_nextbar[0:4] == '0010':
                pattern_count_tied_aug += 1

        # end of song
        d['barcount'] = barcount
        d['tied'] = pattern_count_tied
        d['untied'] = pattern_count_untied
        d['tied_aug'] = pattern_count_tied_aug
        d['untied_aug'] = pattern_count_untied_aug

        # add in some extra stats to look at
        d['year_cat'] = pkdata.get_year_as_category(fileid)
        d['composer'] = pkdata.get_composer(fileid)
        d['rtctype'] = pkdata.get_rtc_type(fileid)
        d['ts'] = pkdata.get_music21_time_signature_clean(fileid)

        # For Jose's code cell at the bottom.
        try:
            d['year'] = pkdata.get_year_as_number(fileid)
        except:
            d['year'] = pd.NA

        rowslist.append(d)

df = pd.DataFrame(rowslist)
df['untied_pct'] = df['untied']/df['barcount']
df['tied_pct'] = df['tied']/df['barcount']
df['untied_aug_pct'] = df['untied_aug']/df['barcount']
df['tied_aug_pct'] = df['tied_aug']/df['barcount']

df_early = df[df['year_cat'] == '1890-1901']
df_late = df[df['year_cat'] == '1902-1919']
df_earlylate = df[ (df['year_cat'] == '1890-1901') | (df['year_cat'] == '1902-1919') ]
df_modern = df[df['year_cat'] == '>1919']

df_joplin = df[df['composer']=='Joplin, Scott']
df_scott = df[df['composer']=='Scott, James']
df_lamb = df[df['composer']=='Lamb, Joseph F.']

print("Early rags: untied/tied:", df_early['untied_pct'].mean(), df_early['tied_pct'].mean())
print("Late  rags: untied/tied:", df_late['untied_pct'].mean(), df_late['tied_pct'].mean())
print("Early+late: untied/tied:", df_earlylate['untied_pct'].mean(), df_earlylate['tied_pct'].mean())
print("Modern rgs: untied/tied:", df_modern['untied_pct'].mean(), df_modern['tied_pct'].mean())

test_early_late_untied = scipy.stats.mannwhitneyu(df_early['untied_pct'], df_late['untied_pct'], alternative='two-sided')
test_early_late_tied   = scipy.stats.mannwhitneyu(df_early['tied_pct'],   df_late['tied_pct'],   alternative='two-sided')

test_old_modern_untied = scipy.stats.mannwhitneyu(df_earlylate['untied'], df_modern['untied_pct'], alternative='two-sided')
test_old_modern_tied   = scipy.stats.mannwhitneyu(df_earlylate['tied_pct'],   df_modern['tied_pct'],   alternative='two-sided')

test_joplin_scott_untied = scipy.stats.mannwhitneyu(df_joplin['untied_pct'], df_scott['untied_pct'], alternative='two-sided')
test_joplin_lamb_untied = scipy.stats.mannwhitneyu(df_joplin['untied_pct'], df_lamb['untied_pct'], alternative='two-sided')
test_scott_lamb_untied = scipy.stats.mannwhitneyu(df_scott['untied_pct'], df_lamb['untied_pct'], alternative='two-sided')

test_joplin_scott_tied = scipy.stats.mannwhitneyu(df_joplin['tied_pct'], df_scott['tied_pct'], alternative='two-sided')
test_joplin_lamb_tied = scipy.stats.mannwhitneyu(df_joplin['tied_pct'], df_lamb['tied_pct'], alternative='two-sided')
test_scott_lamb_tied = scipy.stats.mannwhitneyu(df_scott['tied_pct'], df_lamb['tied_pct'], alternative='two-sided')

print("Joplin tied/untied:", df_joplin['tied_pct'].mean(), df_joplin['untied_pct'].mean())
print("Scott  tied/untied:", df_scott['tied_pct'].mean(), df_scott['untied_pct'].mean())
print("Lamb   tied/untied:", df_lamb['tied_pct'].mean(), df_lamb['untied_pct'].mean())

df_big3 = df[(df['composer']=='Joplin, Scott') | (df['composer']=='Scott, James') | (df['composer']=='Lamb, Joseph F.')]
df_nonbig3 = df[(df['composer']!='Joplin, Scott') & (df['composer']!='Scott, James') & (df['composer']!='Lamb, Joseph F.')]

df_big3_late = df_big3[df_big3['year_cat']=='1902-1919']
df_nonbig3_late = df_nonbig3[df_nonbig3['year_cat']=='1902-1919']

test_big3_others_untied = scipy.stats.mannwhitneyu(df_big3['untied_pct'], df_nonbig3['untied_pct'], alternative='two-sided')
test_big3_others_tied = scipy.stats.mannwhitneyu(df_big3['tied_pct'], df_nonbig3['tied_pct'], alternative='two-sided')

test_big3_others_late_untied = scipy.stats.mannwhitneyu(df_big3_late['untied_pct'], df_nonbig3_late['untied_pct'], alternative='two-sided')
test_big3_others_late_tied = scipy.stats.mannwhitneyu(df_big3_late['tied_pct'], df_nonbig3_late['tied_pct'], alternative='two-sided')

print("Big 3-late t/u     :", df_big3_late['tied_pct'].mean(), df_big3_late['untied_pct'].mean())
print("non big3 3-late t/u:", df_nonbig3_late['tied_pct'].mean(), df_nonbig3_late['untied_pct'].mean())

#%%

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import numpy as np

fig, ax = plt.subplots(1,4, sharey=True)

fig = plt.gcf()
plt.gcf().subplots_adjust(bottom=0.15)
fig.set_size_inches(5, 3)

a=sns.boxplot(data=[df_early['untied_pct'], df_early['tied_pct']], ax=ax[0],palette="Set3", notch=True)
b=sns.boxplot(data=[df_late['untied_pct'], df_late['tied_pct']], ax=ax[1],palette="Set3", notch=True)
c=sns.boxplot(data=[df_earlylate['untied_pct'], df_earlylate['tied_pct']], ax=ax[2],palette="Set3", notch=True)
d=sns.boxplot(data=[df_modern['untied_pct'], df_modern['tied_pct']], ax=ax[3], palette="Set3", notch=True)
#ax[0].set_yticks(np.arange(0, 1, .1))
ax[0].set_ylim(0, 1)
ax[1].set_ylim(0, 1)
ax[2].set_ylim(0, 1)
ax[3].set_ylim(0, 1)
ax[0].set(xticklabels=[], xlabel='1890-1901\n' + r'$\mu\approx$0.19, 0.12')
ax[1].set(xticklabels=[], xlabel='1902-1919\n' + r'$\mu\approx$0.14, 0.24')
ax[2].set(xticklabels=[], xlabel='1890-1919\n' + r'$\mu\approx$0.15, 0.22')
ax[3].set(xticklabels=[], xlabel='post-1919\n' + r'$\mu\approx$0.18, 0.29')
ax[0].set(ylabel='Frequency of pattern per measure')
ax[0].legend((a.artists[0], a.artists[1]), ('Untied', 'Tied'))
#ax[0].set_title('1890-1901', y=-.1)#(xlabel='Time signature and type of density',ylabel='Density')
fig.savefig('expfigs/exp-121-freq-era.pdf', bbox_inches='tight')
plt.show()


#%%
# big three plots - this one is intra-big 3

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import numpy as np

fig, ax =plt.subplots(1,3, sharey=True)

fig = plt.gcf()
plt.gcf().subplots_adjust(bottom=0.15)
fig.set_size_inches(5, 3)

a=sns.boxplot(data=[df_joplin['untied_pct'], df_joplin['tied_pct']], ax=ax[0],palette="Set3", notch=True)
b=sns.boxplot(data=[df_scott['untied_pct'], df_scott['tied_pct']], ax=ax[1],palette="Set3", notch=True)
c=sns.boxplot(data=[df_lamb['untied_pct'], df_lamb['tied_pct']], ax=ax[2],palette="Set3", notch=True)
#ax[0].set_yticks(np.arange(0, 1, .1))
ax[0].set_ylim(0, 1)
ax[1].set_ylim(0, 1)
ax[2].set_ylim(0, 1)

ax[0].set(xticklabels=[], xlabel='1890-1901\n' + r'$\mu\approx$0.19, 0.12')
ax[1].set(xticklabels=[], xlabel='1902-1919\n' + r'$\mu\approx$0.14, 0.24')
ax[2].set(xticklabels=[], xlabel='1890-1919\n' + r'$\mu\approx$0.15, 0.22')

ax[0].set(ylabel='Frequency of pattern per measure')
ax[0].legend((a.artists[0], a.artists[1]), ('Untied', 'Tied'))
#ax[0].set_title('1890-1901', y=-.1)#(xlabel='Time signature and type of density',ylabel='Density')
fig.savefig('expfigs/exp-121-freq-composer.pdf')
plt.show()

#%%
#big three vs everyone else

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import numpy as np

fig, ax =plt.subplots(1,2, sharey=True)

fig = plt.gcf()
plt.gcf().subplots_adjust(bottom=0.15)
fig.set_size_inches(3, 3)

a=sns.boxplot(data=[df_big3_late['untied_pct'], df_big3_late['tied_pct']], ax=ax[0],palette="Set3", notch=True)
b=sns.boxplot(data=[df_nonbig3_late['untied_pct'], df_nonbig3_late['tied_pct']], ax=ax[1],palette="Set3", notch=True)

#ax[0].set_yticks(np.arange(0, 1, .1))
ax[0].set_ylim(0, 1)
ax[1].set_ylim(0, 1)

ax[0].set(xticklabels=[], xlabel='Big 3\n' + r'$\mu\approx$0.22, 0.32')
ax[1].set(xticklabels=[], xlabel='Non Big 3\n' + r'$\mu\approx$0.13, 0.22')

ax[0].set(ylabel='Frequency of pattern per measure')
ax[0].legend((a.artists[0], a.artists[1]), ('Untied', 'Tied'))
#ax[0].set_title('1890-1901', y=-.1)#(xlabel='Time signature and type of density',ylabel='Density')
fig.savefig('expfigs/exp-121-freq-big3-vs-others.pdf', bbox_inches='tight')
plt.show()

#%%
# Author: Jose

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df_yearly = pd.DataFrame({"year": range(df["year"].min(skipna=True),
                                        df["year"].max(skipna=True)+1)})
df_yearly = df_yearly.append({"year": "Unknown"}, ignore_index=True)

df_yearly["compositions"] = 0
df_yearly["tied"] = 0
df_yearly["untied"] = 0
df_yearly["total bars"] = 0
for i, year in enumerate(df["year"]):
    if year is pd.NA:
        df_yearly.loc[df_yearly["year"] == "Unknown", "compositions"] += 1
        df_yearly.loc[df_yearly["year"] == "Unknown", "tied"] += df.iloc[i].loc["tied"]
        df_yearly.loc[df_yearly["year"] == "Unknown", "untied"] += df.iloc[i].loc["untied"]
        df_yearly.loc[df_yearly["year"] == "Unknown", "total bars"] += df.iloc[i].loc["barcount"]
    else:
        df_yearly.loc[df_yearly["year"] == year, "compositions"] += 1
        df_yearly.loc[df_yearly["year"] == year, "tied"] += df.iloc[i].loc["tied"]
        df_yearly.loc[df_yearly["year"] == year, "untied"] += df.iloc[i].loc["untied"]
        df_yearly.loc[df_yearly["year"] == year, "total bars"] += df.iloc[i].loc["barcount"]

df_yearly.insert(4, "total", df_yearly["tied"] + df_yearly["untied"])

df_yearly["tied proportion"] = (df_yearly["tied"]/df_yearly["total bars"]).fillna(0)
df_yearly["untied proportion"] = (df_yearly["untied"]/df_yearly["total bars"]).fillna(0)
df_yearly["total proportion"] = (df_yearly["total"]/df_yearly["total bars"]).fillna(0)


# Number of yearly compositions in compendium.
fig, ax = plt.subplots(figsize=(10, 25))
sns.set_context("paper")
sns.set_color_codes("pastel")
sns.barplot(x="compositions", y="year", data=df_yearly,
            color='b', edgecolor='w', label="Total")
ax.set(xlabel="compositions")
ax.legend(ncol=1, loc="upper right")
ax.set_title('Number of yearly compositions in compendium')
sns.despine(left=True, bottom=True)
fig.savefig("expfigs/yearly-compositions", dpi=300)
plt.show()


# Total "121" pattern occurrences per year.
fig, ax = plt.subplots(figsize=(10, 25))
sns.set_context("paper")
sns.set_color_codes("pastel")
sns.barplot(x="total bars", y="year", data=df_yearly, # delete to remove background plot
            color='b', edgecolor='w', label="Bars")
sns.set_color_codes("muted")
sns.barplot(x="total", y="year", data=df_yearly,
            color='b', edgecolor='w', label="Total")
ax.set(xlabel="occurrences")
ax.legend(ncol=1, loc="upper right")
ax.set_title('Total "121" pattern occurrences per year')
sns.despine(left=True, bottom=True)
fig.savefig("expfigs/121-freq-year-total", dpi=300)
plt.show()

# Proportion of total yearly "121" pattern occurrences to total yearly bars.
fig, ax = plt.subplots(figsize=(10, 25))
sns.set_context("paper")
sns.set_color_codes("pastel")
sns.barplot(x="total proportion", y="year", data=df_yearly,
            color='b', edgecolor='w', label="proportion")
ax.set(xlabel="proportion")
ax.legend(ncol=1, loc="upper right")
ax.set_title('Proportion of total yearly "121" pattern occurrences to total yearly bars')
sns.despine(left=True, bottom=True)
fig.savefig("expfigs/121-freq-year-total-proportion", dpi=300)
plt.show()


# Tied and untied "121" pattern occurrences per year.
fig, ax = plt.subplots(figsize=(10, 25))
sns.set_context("paper")
sns.set_palette("muted")
sns.barplot(x="total bars", y="year", data=df_yearly, # delete to remove background plot
            color='b', edgecolor='w', label="bars")
sns.set_color_codes("pastel")
melted = pd.melt(df_yearly, id_vars=["year"], value_vars=["tied", "untied"],
                 var_name="type", value_name="occurrences")
sns.barplot(x="occurrences", y="year", hue="type", data=melted,
            edgecolor='w')
ax.legend(ncol=1, loc="upper right", title="Type")
ax.set_title('Tied and untied "121" pattern occurrences per year')
sns.despine(left=True, bottom=True)
fig.savefig("expfigs/121-freq-year-type", dpi=300)
plt.show()

# Proportion of different "121" pattern occurrences to total yearly bars.
fig, ax = plt.subplots(figsize=(10, 25))
sns.set_context("paper")
sns.set_palette("pastel")
melted = pd.melt(df_yearly,
                 id_vars=["year"],
                 value_vars=["tied proportion", "untied proportion"],
                 var_name="type", value_name="proportion")
sns.barplot(x="proportion", y="year", hue="type", data=melted,
            edgecolor='w')
ax.legend(ncol=1, loc="upper right", title="Type")
ax.set_title('Proportion of different "121" pattern occurrences to total yearly bars')
sns.despine(left=True, bottom=True)
fig.savefig("expfigs/121-freq-year-type-proportion", dpi=300)
plt.show()


# if we have more patters we can also look at the ratio of 121 year by year.
