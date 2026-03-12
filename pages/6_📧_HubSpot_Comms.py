"""Page wrapper — HubSpot Communications analysis"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.hubspot_comms import main
main()
