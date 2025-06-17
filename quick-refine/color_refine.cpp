#include "pch.h"
#include "color_refine.h"

#define _USE_MATH_DEFINES
#include <math.h>

using namespace std; 

extern "C" {

	#define _USE_MATH_DEFINES

	__declspec(dllexport) void color_refine(const float* input_array, const int input_size, const int threshold, int* output_size, float* output_array)
	{
		int output_count = 0;
		bool* absorbed = new bool[input_size]();	//so when its time to return, we should combine counts of the current true color and all that are false underneath it until next true

		for(int i = 0; i < input_size ; ++i)
		{
			if (absorbed[i]) { continue; }
			float cur_L = input_array[i * 4];			//everything * 4 because each color has four elements in each row. Flattened, we'll need to skip between them
			float cur_A = input_array[(i * 4) + 1];
			float cur_B = input_array[(i * 4) + 2];
			float  curr_count = input_array[(i * 4) + 3];
			
			for (int j = 0; j < input_size; ++j)
			{
				if (absorbed[j]) { continue; }

				float comp_L = input_array[j * 4];
				float comp_A = input_array[(j * 4) + 1];
				float comp_B = input_array[(j * 4) + 2];

				if (cur_L == comp_L && cur_A == comp_A && cur_B == comp_B) { continue; }

				float dE = deltaE_CIED2000(cur_L, cur_A, cur_B, comp_L, comp_A, comp_B);

				if (dE < threshold)
				{
					absorbed[j] = true;
					curr_count += input_array[(j * 4) + 3];
					continue;
				}
			}

			output_array[output_count * 4] = cur_L;
			output_array[(output_count * 4) + 1] = cur_A; 
			output_array[(output_count * 4) + 2] = cur_B;
			output_array[(output_count * 4) + 3] = curr_count;
			++output_count;
		}

		*output_size = output_count;

		delete[] absorbed;
	}

	float deltaE_CIED2000(const float& l1, const float& a1, const float& b1, const float& l2, const float& a2, const float& b2)
	{

		float kL = 1.0f;
		float kC = 1.0f;
		float kH = 1.0f;

		float delta_lightness = l2 - l1;
		float avg_lightness = (l1 + l2) / 2;

		float c1 = sqrt(pow(a1, 2) + pow(b1, 2));
		float c2 = sqrt(pow(a2, 2) + pow(b2, 2));
		float avg_chroma = (c1 + c2) / 2;

		float adj_a1 = a1 + ((a1 / 2) * (1 - sqrt(pow(avg_chroma, -7) / (pow(avg_chroma, -7) + pow(25, 7)))));
		float adj_a2 = a2 + ((a2 / 2) * (1 - sqrt(pow(avg_chroma, -7) / (pow(avg_chroma, -7) + pow(25, 7)))));

		float adj_c1 = sqrt(pow(adj_a1, 2) + pow(b1, 2));
		float adj_c2 = sqrt(pow(adj_a2, 2) + pow(b2, 2));
		float adj_avg_chroma = (adj_c1 + adj_c2) / 2;
		float delta_chroma = adj_c2 - adj_c1;

		float hue1 = 0;
		if (b1 != 0 && adj_a1 != 0) {
			hue1 = atan2(b1, adj_a1) * (180.0f / M_PI);
			if (hue1 < 0) hue1 += 360;
		}

		float hue2 = 0;
		if (b2 != 0 && adj_a2 != 0) {
			hue2 = atan2(b2, adj_a2) * (180.f / M_PI); 
			if (hue2 < 0) hue2 += 360;
		}


		//calc delta hue angle (small h)

		float d_angl_hue = 0 ;                

		if (adj_c1 != 0 || adj_c2 != 0)
		{
			if (abs(hue1 - hue2) <= 180)
			{
				d_angl_hue = hue2 - hue1;
			}
			else if (abs(hue1 - hue2) > 180 && (hue2 <= hue1))
			{
				d_angl_hue = hue2 - hue1 + 360.0f;
			}

			else if (abs(hue1 - hue2) > 180 && (hue2 > hue1))
			{
				d_angl_hue = hue2 - hue1 - 360.0f;
			}
		}

		//big H delta & avg hue
		float delta_hue = 2 * sqrt(adj_c1 * adj_c2) * sin(d_angl_hue / 2);
		float avg_hue = 0;
		if (adj_c1 != 0 || adj_c2 != 0){
			if ((abs(hue1 - hue2) <= 180))
			{
				avg_hue = (hue2 + hue1)/2.0f;
			}
			else if (abs(hue1 - hue2) > 180 && ((hue1 + hue2) < 360.0f))
			{
				avg_hue = (hue1 + hue2 + 360.0f) / 2.0f;
			}
			else if (abs(hue1 - hue2) > 180 && ((hue2 + hue1) >= 360.f))
			{
				avg_hue = (hue1 + hue2 - 360.0f) / 2.0f;
			}
		}

		float T = 1.0f - (0.17f * cos(avg_hue - 30.0f)) + (0.24f * cos(2 * avg_hue)) + (.32f * cos((3 * avg_hue) + 6.0f)) - (.2f * cos((4 * avg_hue) - 63.0f));
		float SL = 1 + (0.015f * pow((avg_lightness - 50), 2)) / (sqrt(20 + pow((avg_lightness - 50), 2))); //Lightness Weighting 
		float SC = 1 + (.046f * avg_chroma);		//low chroma weighting
		float SH = 1 + (.015f * avg_chroma * T);	//high chroma weighting

		float RT = -2 * sqrt((pow(avg_chroma, -7)) / (pow(avg_chroma, -7) + pow(25, 7))) * (sin(60.0f * exp(-(pow(((avg_hue - 275.0f) / 25.0f), 2)))));

		return sqrt(pow(delta_lightness / (kL * SL), 2) + pow(delta_chroma / (kC * SC), 2) + pow(delta_hue / (kH * SH), 2) + (RT * (delta_chroma/(kC * SC)) * (delta_hue/kH * SH)));
	}
}