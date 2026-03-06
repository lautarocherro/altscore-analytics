"""Page wrapper — Stage Funnel analysis"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.deal_stage_funnel import main
main()
