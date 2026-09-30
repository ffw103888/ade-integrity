"""Saved quantitative comparison against scipy; run from repository root."""
import random
from scipy import stats
from ade_integrity.core import judge_paired
def main():
    rng=random.Random(210930); max_p=0.0; max_ci=0.0; count=0
    for n in (6,7,32,100):
        for alpha in (.01,.05,.10):
            for shift in (-.5,0,.5):
                values=[rng.gauss(shift,1) for _ in range(n)]
                ours=judge_paired(values,alpha=alpha); ref=stats.ttest_1samp(values,0).pvalue
                ci=stats.t.interval(1-alpha,n-1,loc=sum(values)/n,scale=stats.sem(values))
                max_p=max(max_p,abs(ours["p_value"]-float(ref)))
                max_ci=max(max_ci,max(abs(ours["confidence_interval"][i]-ci[i]) for i in (0,1)))
                count+=1
    result={"cases":count,"max_p_error":max_p,"max_ci_error":max_ci}
    if max_p>1e-8 or max_ci>1e-8: raise AssertionError(result)
    print(result)
if __name__=="__main__": main()
